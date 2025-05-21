from dataclasses import dataclass
import subprocess
import importlib.resources
from pathlib import Path
import os
from pathlib import Path
import yaml
from typing import Any, Dict

def get_evapro_path() -> str:
    try:
        from importlib.metadata import distribution
        dist = distribution("evapro")  # 替换为你的包名
        scripts_dir = Path(dist.locate_file("")).parent.parent.parent / "bin"
        return str(scripts_dir / "evapro")
    except Exception:
        return "路径未找到"

@dataclass
class cronlist(object):
    """Manage cron jobs for evapro.
    """
    cronnode: str = None
    program: str = None
    def __post_init__(self):
        self.program = get_evapro_path()

    def add_cron(self):
        conf = _get_yaml_data(importlib.resources.path("evapro.config", "evapro.yaml"))
        import socket
        if 'cronnode' not in conf:
            conf['cronnode'] = socket.gethostname()
            with open(confpath, 'w', encoding='utf-8') as f:
                yaml.safe_dump(conf, f, allow_unicode=True, sort_keys=False)
        else:
            if conf['cronnode'] != socket.gethostname():
                print(f"当前主机名与配置文件中的主机名不匹配: {socket.gethostname()} != {conf['cronnode']}\n请更换节点")
                return

        p = subprocess.Popen('crontab -l', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdoutput, _ = p.communicate()
        crontable = str(stdoutput,'utf-8').split('\n')
        need_addcron = 1
        for line in crontable:
            if line.find(f'{os.path.basename(self.program)} cron'.format()) > 0:
                need_addcron = 0
        if need_addcron == 1:
            #run cron project per 2 hours
            line = f'0 */2 * * * {self.program} cron'
            crontable.append(line)

            pipe = os.popen('crontab', 'w')
            for line in crontable:
                if line == '':
                    continue
                pipe.write(line+'\n')
            pipe.flush()
            pipe.close()

def get_dbpath() -> Path:
    """Get syncdbpath.db path
    """
    confpath = importlib.resources.path("evapro.config", "evapro.yaml")
    if os.path.isfile(confpath):
        conf = _get_yaml_data(confpath)
        if 'syncproject' in conf:
            if os.path.isfile(conf['syncproject']):
                return conf['syncproject']
            else:
                print(f"指定的数据库路径不存在: {confpath}")
                return None

def set_dbpath(syncdbdir: str) -> None:
    """Set syncdbpath.db path
    """
    confpath = importlib.resources.path("evapro.config", "evapro.yaml")
    content = f'syncproject: {syncdbdir}/syncproject.db'

    try:
        conf = _get_yaml_data(confpath)
        # 初始化autoconf节点如果不存在
        conf['syncproject'] = content
        # 保存修改后的配置
        with open(confpath, 'w', encoding='utf-8') as f:
            yaml.safe_dump(conf, f, allow_unicode=True, sort_keys=False)
        
        print(f'请修改配置文件中的lims数据库配置\n{confpath}')
            #return Path(default_confi
    except PermissionError as e:
        print(f"权限不足无法修改配置文件: {e.filename}")
    except Exception as e:
        print(f"保存配置时发生错误: {str(e)}")

def _get_yaml_data(yaml_file: str) -> Dict[str, Any]:
    """Load and parse YAML configuration file.
    
    Args:
        yaml_file: Path to the YAML configuration file
        
    Returns:
        Dict[str, Any]: Parsed YAML data as dictionary
        
    Raises:
        yaml.YAMLError: If the YAML file is malformed
        FileNotFoundError: If the specified file does not exist
        
    Example:
        >>> config = _get_yaml_data("config.yaml")
    """
    with open(yaml_file, "r", encoding="utf-8") as file:
        file_data = file.read()
        return yaml.safe_load(file_data)

