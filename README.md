# evapro 命令行工具使用说明

## 安装
```bash
pip install evapro
```
安装成功后会在conda环境的bin下生成evapro主程序，可在命令行直接使用该程序，例如 /seqyuan/Miniconda3/envs/annoeva/bin/evapro

## 命令列表

### 初始化数据库

这个命令仅需要程序`管理员`执行一次！！

```bash
evapro init -d /path/to/dbdir
```

**参数说明**:
- `-d/--syncdbdir`: 指定数据库存储目录路径

**功能**:
1. 创建 syncproject.db 数据库
2. 创建所需数据表  
3. 设置数据库文件和目录权限为 777

### 查看修改配置文件路径
初始化完成后，需要手动修改evapro的配置文件，以使其能够正确访问:
- lims数据库
- annoeva程序
- annoeva配置文件

```bash
evapro conf
```

**功能**:
1. 显示当前使用的配置文件路径
2. 支持手动编辑配置文件

配置文件内容如下：
```
syncproject: /path/syncproject.db
# 数据库地址，通过evapro init命令创建的
cronnode: bj-sci-login
# 把项目从lims数据库同步到syncproject.db计划任务的执行节点，这是为了防止多节点执行造成的冲突
syn_lims_time: 2025-05-21 13:56:35
# 上次从lims同步项目的时间，下次会从这个时间之后同步项目
annoevaconf: /seqyuan/miniconda3/envs/annoeva/lib/python3.11/site-packages/annoeva/config/evaconf.yaml
# annoeva的配置文件，这个文件记录的产品类型的项目才会被evapro自动加入到annoeva流水线监控
annoeva:  /seqyuan/miniconda3/envs/annoeva/bin/annoeva
# 流水线程序annoeva的程序路径

# 下面两项是lims数据库的配置，根据实际需要进行修改
cloud_message_info_db:
  host: mysql.rds.aliyuncs.com
  port: 3307
  user: cloud_message
  passwd: 
  db: cloud_message_info
  charset: utf8

lims3_db:
  host: mysql.rds.aliyuncs.com
  port: 3307
  user: 
  passwd:
  db: lims3
  charset: utf8
```

### 同步 LIMS 数据
`这个命令是为程序管理员准备`

```bash
/path/evapro lims2evapro
```

**功能**:
1. 从 LIMS 系统同步分析项目数据到本地数据库
2. 建议每4小时执行一次(需配置计划任务)

**配置计划任务**:
这个命令需要程序`管理员`加入到crontab计划任务即可实现定时自动从lims数据库导入项目到syncproject.db 数据库。

**操作步骤**:
1. 执行 `crontab -e` 打开crontab任务列表
2. 添加以下内容到新的一行:
```
0 4 * * * /seqyuan/miniconda3/envs/annoeva/bin/evapro cron
``` 
3. 保存退出(`:wq`)

### 添加项目到监控系统
`这个命令需要项目负责人执行`

```bash
/path/evapro cron
```

**功能**:
1. 检查数据库中的项目
2. 将新项目添加到 annoeva 监控系统，只会添加运行账户的项目到运行账户的annoeva监控

**自动计划任务**:
- 首次运行`evapro`程序后，会自动将`evapro cron`命令添加到运行账户的crontab计划任务列表
- 默认执行频率: 每2小时执行一次

## 注意事项

**重要提示**:
1. 初始化时需要确保对指定目录有写入权限
2. 同步 LIMS 数据需要正确配置数据库连接信息
3. 自动设置 777 权限需要目录的属主执行evapro程序
