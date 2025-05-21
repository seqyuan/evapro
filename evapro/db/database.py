import os
import sqlite3
import getpass
from dataclasses import dataclass, field
from pandas import read_sql, DataFrame

@dataclass
class SQLiteDB:
    """
    A class to manage SQLite database operations for project tracking.
    
    Attributes:
        dbpath (str): Path to the SQLite database file
        conn (sqlite3.Connection): Database connection object
        cur (sqlite3.Cursor): Database cursor object
    """

    dbpath: str
    conn: sqlite3.Connection = field(init=False)
    cur: sqlite3.Cursor = field(init=False)

    def __post_init__(self):
        # 确保数据库目录存在
        db_dir = os.path.dirname(os.path.abspath(os.path.expanduser(self.dbpath)))
        os.makedirs(db_dir, exist_ok=True)
        
        # 使用check_same_thread=False允许多线程访问
        self.conn = sqlite3.connect(
            os.path.expanduser(self.dbpath), 
            check_same_thread=False,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        #self.conn.execute('PRAGMA journal_mode=WAL')  # 启用写入日志模式
        self.cur = self.conn.cursor()

    def crt_tb_sql(self) -> None:
        """Create the projects table in the database if it doesn't exist.

        The table contains the following columns:

        id: primary key
        user: user name
        proid: subproject id, unique not null
        ptype: project product type, which product type's autoconf.py program in annoeva.yaml needs to be invoked
        workdir: workdir path
        dirstat: workdir status [Y|N], default: N
        info: info.xlsx file status [Y|N], default: N
        data: data status [Y|N|err], default: N
        autoconf: auto config status [Y|N|err], default: N
        conf_stde: auto config stderr
        worksh: work.sh file path
        pid: work.sh run pid
        p_args: work.sh run command args
        stime: work.sh execute start time
        etime: work.sh execute end time
        pstat: project status, work.sh execute status [run|done|err|-], default: -
        run_num: project re-run number
        """
        crt_tb_sql_c = """
        create table if not exists projects(
        id integer primary key autoincrement unique not null,
        user text,
        proid text unique not null,
        ptype text,
        workdir text,
        dirstat text,
        info text,
        data text,
        autoconf text,
        conf_stde text,
        worksh text,
        pid integer,
        p_args text,
        stime text,
        etime text,
        pstat text,
        run_num integer
        );"""

        try:
            self.cur.execute(crt_tb_sql_c)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"创建 projects 数据库表失败: {str(e)}")
            raise

    def crt_allpro_tb_sql(self) -> None:
        """Create the all_ana_projects table in the database if it doesn't exist.

        The table contains the following columns:

        id: primary key
        user: user name
        proid: subproject id, unique not null
        ptype: project product type
        isautoflow: is flow line product type, [Y|N]
        workdir: workdir path
        isadd2annoeva: is add to annoeva monitor, [Y|N]
        """
        crt_allpro_tb_sql_c = """
        create table if not exists all_ana_projects(
        id integer primary key autoincrement unique not null,
        user text,
        proid text unique not null,
        ptype text,
        isautoflow text,
        workdir text,
        isadd2annoeva text
        );"""

        try:
            self.cur.execute(crt_allpro_tb_sql_c)
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"创建 all_ana_projects 数据库表失败: {str(e)}")
            raise

    def insert_tb_sql(self, user: str, proid: str, ptype: str) -> None:
        """Insert a new project record into the database.
        
        Args:
            user (str): User Account
            proid (str): Project ID
            ptype (str): Project type
        """
        insert_sql = "insert into projects (user, proid, ptype, workdir, dirstat, info, data, autoconf, pstat, run_num) values (?,?,?,?,?,?,?,?,?,?)"
        self.cur.execute(insert_sql, (user, proid, ptype, '', 'N', 'N', 'N', 'N', '-', 0))
        self.conn.commit()

    def insert_allpro_tb_sql(self, user: str, proid: str, ptype: str, isautoflow: str, workdir: str) -> None:
        """Insert a new all_ana_projects record into the database.
        
        Args:
            user (str): User name
            proid (str): Project ID
            ptype (str): Project type
            isautoflow (str): Is auto flow [Y|N]
            workdir (str): Work directory path
        """
        insert_sql = "insert into all_ana_projects (user, proid, ptype, isautoflow, workdir, isadd2annoeva) values (?,?,?,?,?,?)"
        self.cur.execute(insert_sql, (user, proid, ptype, isautoflow, workdir, 'N'))
        self.conn.commit()

    def update_tb_value_sql(self, proid: str, name: str, value: str, table: str="projects") -> None:
        """Update a specific field value for a project record.
        
        Args:
            proid (str): Project ID to update
            name (str): Field name to update
            value (str): New value to set
            table (str): Table name (default: "projects")
        """
        update_sql = f"update '{table}' set '{name}'='{value}' where proid='{proid}'"
        self.cur.execute(update_sql)
        self.conn.commit()

    def query_record(self, key: str, value: str) -> DataFrame:
        """Query project records matching the given key-value pair.
        
        Args:
            key (str): Column name to query
            value (str): Value to match
            
        Returns:
            DataFrame: Pandas DataFrame containing matching records
            
        Raises:
            ValueError: If key is not a valid column name
        """
        valid_columns = ['id', 'user', 'proid', 'ptype', 'workdir', 'dirstat', 
                        'info', 'data', 'autoconf', 'conf_stde', 'worksh', 
                        'pid', 'p_args', 'stime', 'etime', 'pstat', 'run_num']
                        
        if key not in valid_columns:
            raise ValueError(f"Invalid column name: {key}")
            
        query = "SELECT * FROM projects WHERE ? = ?"
        df = read_sql(query, con=self.conn, params=(key, value))
        return df
    
    def delete_project(self, projectid: str) -> None:
        """Delete a project record and stop any running processes.
        
        Args:
            projectid (str): Project ID to delete
            
        Raises:
            sqlite3.Error: If database operation fails
        """
        try:
            username = getpass.getuser()
            query = "SELECT * FROM projects WHERE proid = ? AND user = ?"
            df = read_sql(query, con=self.conn, params=(projectid, username))
            if df.shape[0] == 0:
                print(f"project {projectid} not found or not owned by {username}")
                return
           
            self.cur.execute("DELETE FROM projects WHERE proid = ?", (projectid,))            
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            self.conn.rollback()
            raise

    def close_db(self) -> None:
        """Close the database connection and cursor."""
        self.cur.close()
        self.conn.close()
