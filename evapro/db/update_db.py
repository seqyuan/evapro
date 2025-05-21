import pymysql
import datetime
from datetime import timedelta
import importlib.resources
import yaml
import subprocess
import getpass
from pandas import read_sql
from evapro.db import SQLiteDB

def _get_yaml_data(yaml_file: str) -> dict:
    """Load and parse YAML configuration file.
    
    Args:
        yaml_file: Path to the YAML configuration file
        
    Returns:
        dict: Parsed YAML data
        
    Raises:
        yaml.YAMLError: If the YAML file is malformed
        FileNotFoundError: If the specified file does not exist
    """
    with open(yaml_file, "r", encoding="utf-8") as file:
        return yaml.safe_load(file)

def get_analysis_project(connection, create_date):
    """
    获取用户的分析项目数据
    
    参数:
        connection: 数据库连接对象
        info_user_id: 用户ID
        create_date: 创建日期阈值 (格式: 'YYYY-MM-DD HH:MM:SS')
    
    返回:
        DataFrame 包含 project_code, product_ID, task_name
    """
    query = """
        SELECT 
            project_code, 
            product_parent_id, 
            product_id,
            task_name,
            info_user_id
        FROM 
            tb_info_sequence_bill 
        WHERE 
            create_date > %s 
            AND ANALYSIS_TYPE = 1
    """
    
    try:
        df = read_sql(query, con=connection, params=(create_date,))
        df['product_ID'] = df['product_parent_id'].astype(str) + "-" + df['product_id'].astype(str)
        df.drop(['product_parent_id', 'product_id'], axis=1, inplace=True)
        return df
    except Exception as e:
        print(f"查询出错: {e}")
        return pd.DataFrame()

def product_type(CONN):
    """Get product id and name from lims"""
    df = pd.read_sql('SELECT PRODUCT_LIMS_ID, introduction FROM project_online_product_type', con=CONN)
    df = df[df['PRODUCT_LIMS_ID'] != ""]
    df["PRODUCT_LIMS_ID"] = df["PRODUCT_LIMS_ID"].str.split(",")
    df = df.explode("PRODUCT_LIMS_ID")
    df["PRODUCT_LIMS_ID"] = df["PRODUCT_LIMS_ID"].str.strip()
    df = df[df['PRODUCT_LIMS_ID'] != ""]
    df.index = df['PRODUCT_LIMS_ID']
    df = df.drop_duplicates('PRODUCT_LIMS_ID')
    del df['PRODUCT_LIMS_ID']
    df.columns = ['PRODUCT']
    return df

def lims2evaproDB() -> None:
    """Sync data from LIMS to evapro database"""
    try:
        confpath = importlib.resources.path("evapro.config", "evapro.yaml")
        conf = _get_yaml_data(confpath)
        pre_syn_time = conf['syn_lims_time']
        now = datetime.datetime.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')

        one_week_ago = now - timedelta(weeks=1)
        one_week_ago_str = one_week_ago.strftime("%Y-%m-%d %H:%M:%S")

        conn = pymysql.connect(**conf['cloud_message_info'])
        conn_bill = pymysql.connect(**conf['lims3'])

        df_ana_pro = get_analysis_project(conn_bill, pre_syn_time)
        pid_name = product_type(conn)
        df_ana_pro['PRODUCT'] = pid_name.loc[df_ana_pro['product_ID'], "PRODUCT"].to_list()
        df_ana_pro['workdir'] = ''

        path_df = pd.read_sql('SELECT SUB_PROJECT_ID, PATHWAY FROM project_online_backup_info where MISSION_END_DATE>"2025-04-01"', con=conn)
        path_df.index = path_df['SUB_PROJECT_ID']
        path_df = path_df.drop_duplicates('SUB_PROJECT_ID')
        path_df = path_df[path_df['SUB_PROJECT_ID'].isin(df_ana_pro['project_code'])]
        df_ana_pro['workdir'] = path_df.loc[df_ana_pro['project_code'], "PATHWAY"].to_list()

        annoeva_conf = _get_yaml_data(conf['annoevaconf'])
        autoflow_products = annoeva_conf['autoconf'].keys()

        tbj = SQLiteDB(dbpath=f"{conf['syncproject']}/syncproject.db")

        for i, row in df_ana_pro.iterrows():
            try:
                isautoflow = 'Y' if row['PRODUCT'] in autoflow_products else 'N'
                tbj.insert_allpro_tb_sql(row['info_user_id'], row['project_code'], row['PRODUCT'], isautoflow, row['workdir'])
            except Exception as e:
                print(f"Error inserting project {row['project_code']}: {e}")
                continue

        tbj.close_db()
        conn.close()
        conn_bill.close()

        conf['syn_lims_time'] = now_str
        with open(confpath, 'w', encoding='utf-8') as f:
            yaml.safe_dump(conf, f, allow_unicode=True, sort_keys=False)

    except Exception as e:
        print(f"Error in lims2evaproDB: {e}")
        raise

def add_project2annoeva() -> None:
    """Add projects to annoeva monitoring system"""
    try:
        confpath = importlib.resources.path("evapro.config", "evapro.yaml")
        conf = _get_yaml_data(confpath)
        pro_tbj = SQLiteDB(dbpath=f"{conf['syncproject']}/syncproject.db")
        
        user = getpass.getuser()
        query = """
            SELECT 
                proid, 
                ptype, 
                workdir
            FROM 
                all_ana_projects 
            WHERE 
                user = %s 
                AND isadd2annoeva = 'N' 
                AND workdir != ''
        """
        df = read_sql(query, con=pro_tbj.conn, params=(user,))
        for i, row in df.iterrows():
            try:
                cmd = f"{conf['annoeva']} addproject -p {row['proid']} -t {row['ptype']} -d {row['workdir']}"
                p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdo, stde = p.communicate()  
                pro_tbj.update_tb_value_sql(row['proid'], 'isadd2annoeva', 'Y', table='all_ana_projects')
            except Exception as e:
                print(f"Error adding project {row['proid']}: {str(stde,'utf-8')}")
                continue

        pro_tbj.close_db()
    except Exception as e:
        print(f"Error in add_project2annoeva: {e}")
        raise
