#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync projects between personal db and lims db
"""

import os
import warnings
from typing import Optional
from pathlib import Path

import click
from evapro.db.database import SQLiteDB 

from evapro.db.update_db import lims2evaproDB, add_project2annoeva
from evapro.config import (
    cronlist,
    set_dbpath
)

warnings.filterwarnings("ignore")

@click.group()
def main() -> None:
    """Main command group for evapro CLI.
    This serves as the entry point for all subcommands.
    """
    crnlist = cronlist()
    #crnlist.add_cron()

# ------------------------------------------------------------------------------------
@main.command(name="init")
@click.option('--syncdbdir', '-d', default=None,
              help="paht to store the database, syncproject.db")
def init_cli(syncdbdir: str) -> None:
    """
    Initialize the database and add projects to the monitoring system.
    """
    set_dbpath(syncdbdir)

    tbj = SQLiteDB(dbpath=f'{syncdbdir}/syncproject.db')
    tbj.crt_tb_sql()
    tbj.crt_allpro_tb_sql()
    tbj.close_db()

# ------------------------------------------------------------------------------------
@main.command(name="lims2evapro")
def lims2eva_cli() -> None:
    """Sync lims analysis projects to syncproject.db  all_ana_projects table
    需要加入管理账户的计划任务，每4h执行一次
    """
    lims2evaproDB()

# ------------------------------------------------------------------------------------
@main.command(name="cron")
def cron_cli() -> None:
    """遍历evapro数据库所有项目，检查是否有新的项目需要添加到annoEva
    """
    add_project2annoeva() 
    
# ------------------------------------------------------------------------------------
@main.command(name="conf")
def conf_cli() -> None:
    """check config file
    """
    confpath = importlib.resources.path("evapro.config", "evapro.yaml")
    print(f"配置文件路径: {confpath}")


# ------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()

