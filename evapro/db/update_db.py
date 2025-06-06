import pymysql
import datetime
from datetime import timedelta
import importlib.resources
import yaml
import subprocess
import getpass
from pandas import read_sql, DataFrame
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

def get_analysis_project(connection, now_date):
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
            create_date,
            info_date,
            project_code, 
            product_parent_id, 
            product_id,
            task_name,
            info_user_id
        FROM 
            tb_info_sequence_bill 
        WHERE 
            info_date > %s 
            AND ANALYSIS_TYPE = 1
    """
    
    try:
        df = read_sql(query, con=connection, params=(now_date,))
        df['product_ID'] = df['product_parent_id'].astype(str) + "-" + df['product_id'].astype(str)
        df.drop(['product_parent_id', 'product_id'], axis=1, inplace=True)
        return df
    except Exception as e:
        print(f"查询出错: {e}")
        return DataFrame()

def product_type(CONN):
    """Get product id and name from lims"""
    df = read_sql('SELECT PRODUCT_LIMS_ID, introduction FROM project_online_product_type', con=CONN)
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

def update_project_workdir() -> None:
    confpath = importlib.resources.path("evapro.config", "evapro.yaml")
    with confpath as default_config:
        conf = _get_yaml_data(default_config)
        
    tbj = SQLiteDB(dbpath=f"{conf['syncproject']}")
    query = "SELECT proid FROM all_ana_projects WHERE workdir = ''"
    df = read_sql(query, con=tbj.conn)
    if df.shape[0] == 0:
        tbj.close_db()
        return

    conn = pymysql.connect(**conf['cloud_message_info'])
    query = f"""SELECT SUB_PROJECT_ID, PATHWAY FROM project_online_backup_info WHERE PATHWAY != '' AND SUB_PROJECT_ID IN ({','.join([f"'{item}'" for item in df['proid']])})"""
    path_df = read_sql(query, conn)
    
    for i, row in path_df.iterrows():
        try:
            update_sql = f"update all_ana_projects set workdir ='{row['PATHWAY']}' where proid='{row['SUB_PROJECT_ID']}'"
            tbj.cur.execute(update_sql)
            tbj.conn.commit()
        except Exception as e:
            print(f"Error updating workdir for project {row['SUB_PROJECT_ID']}: {e}")
            continue
    tbj.close_db()
    conn.close()
    
def update_project_user() -> None:
    confpath = importlib.resources.path("evapro.config", "evapro.yaml")
    with confpath as default_config:
        conf = _get_yaml_data(default_config)
        
    tbj = SQLiteDB(dbpath=f"{conf['syncproject']}")
    query = "SELECT proid FROM all_ana_projects WHERE user IS NULL"
    df = read_sql(query, con=tbj.conn)
    if df.shape[0] == 0:
        tbj.close_db()
        return

    conn = pymysql.connect(**conf['lims3'])
    query = f"""SELECT project_code, info_user_id FROM tb_info_sequence_bill WHERE info_user_id != '' AND project_code IN ({','.join([f"'{item}'" for item in df['proid']])})"""
    path_df = read_sql(query, conn)
    
    for i, row in path_df.iterrows():
        try:
            update_sql = f"update all_ana_projects set user ='{row['info_user_id']}' where proid='{row['project_code']}'"
            tbj.cur.execute(update_sql)
            tbj.conn.commit()
        except Exception as e:
            print(f"Error updating user for project {row['project_code']}: {e}")
            continue
    tbj.close_db()
    conn.close()

def lims2evaproDB() -> None:
    """Sync data from LIMS to evapro database"""
    try:
        confpath = importlib.resources.path("evapro.config", "evapro.yaml")
        with confpath as default_config:
            conf = _get_yaml_data(default_config)

        pre_syn_time = conf['syn_lims_time']
        now = datetime.datetime.now()
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')

        one_week_ago = now - timedelta(weeks=6)
        one_week_ago_str = one_week_ago.strftime("%Y-%m-%d %H:%M:%S")

        conn = pymysql.connect(**conf['cloud_message_info'])
        conn_bill = pymysql.connect(**conf['lims3'])

        df_ana_pro = get_analysis_project(conn_bill, pre_syn_time)
        pid_name = product_type(conn)
        
        # ---
        not_add_ana_df = df_ana_pro[df_ana_pro['product_ID'].isin(pid_name.index)==False]
        not_add_ana_df.to_csv("~/not_add_ana_df.tsv", sep="\t")
        # ---
        
        df_ana_pro = df_ana_pro[df_ana_pro['product_ID'].isin(pid_name.index)==True]
        df_ana_pro['PRODUCT'] = pid_name.loc[df_ana_pro['product_ID'], "PRODUCT"].to_list()
        df_ana_pro['workdir'] = ''

        path_df = read_sql('SELECT SUB_PROJECT_ID, PATHWAY FROM project_online_backup_info where MISSION_END_DATE>"2025-04-01"', con=conn)
        path_df.index = path_df['SUB_PROJECT_ID']
        path_df = path_df.drop_duplicates('SUB_PROJECT_ID')
        path_df = path_df[path_df['SUB_PROJECT_ID'].isin(df_ana_pro['project_code'])]

        # ---
        have_workdir_df = df_ana_pro[df_ana_pro['project_code'].isin(path_df['SUB_PROJECT_ID'])]
        df_ana_pro.loc[have_workdir_df.index, 'workdir'] = path_df.loc[have_workdir_df['project_code'], "PATHWAY"].to_list()
        # ---

        annoeva_conf = _get_yaml_data(conf['annoevaconf'])
        autoflow_products = annoeva_conf['autoconf'].keys()
        tbj = SQLiteDB(dbpath=f"{conf['syncproject']}")

        for i, row in df_ana_pro.iterrows():
            create_date = row['create_date'].strftime('%Y-%m-%d %H:%M:%S')
            info_date = row['info_date'].strftime('%Y-%m-%d %H:%M:%S')
            try:
                isautoflow = 'Y' if row['PRODUCT'] in autoflow_products else 'N'
                tbj.insert_allpro_tb_sql(row['info_user_id'], row['project_code'], create_date, info_date, row['PRODUCT'], isautoflow, row['workdir'],)
            except Exception as e:
                print(f"Error inserting project {row['project_code']}: {e}")
                continue

        tbj.close_db()
        conn.close()
        conn_bill.close()

        conf['syn_lims_time'] = now_str
        with open(default_config, 'w', encoding='utf-8') as f:
            yaml.safe_dump(conf, f, allow_unicode=True, sort_keys=False)

    except Exception as e:
        print(f"Error in lims2evaproDB: {e}")
        raise

def add_project2annoeva() -> None:
    """Add projects to annoeva monitoring system"""
    try:
        confpath = importlib.resources.path("evapro.config", "evapro.yaml")
        with confpath as default_config:
            conf = _get_yaml_data(default_config)
        pro_tbj = SQLiteDB(dbpath=f"{conf['syncproject']}")
        ADuser = conf['ADuser']
        
        user = getpass.getuser()
        if user in ADuser.keys():
            user = ADuser[user]
        
        query = """
            SELECT 
                proid, 
                ptype, 
                workdir
            FROM 
                all_ana_projects 
            WHERE 
                `user` = ?
                AND isadd2annoeva = 'N' 
                AND workdir != ?
        """
        df = read_sql(query, con=pro_tbj.conn, params=(user, ''))
        for i, row in df.iterrows():
            try:
                cmd = f"{conf['annoeva']} addproject -p {row['proid']} -t {row['ptype']} -d {row['workdir']}"
                p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdo, stde = p.communicate()  
                
                pro_tbj.update_tb_value_sql(row['proid'], 'isadd2annoeva', 'Y', table='all_ana_projects')
                # webhook 提醒
            except Exception as e:
                print(f"Error adding project {row['proid']}: {str(stde,'utf-8')}")
                continue
            
        pro_tbj.close_db()
    except Exception as e:
        print(f"Error in add_project2annoeva: {e}")
        raise
