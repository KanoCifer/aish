import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 日志格式（包含时间）
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# 日志最大大小：1MB
MAX_LOG_SIZE = 1 * 1024 * 1024  # 1MB
# 保留的备份日志数量
BACKUP_COUNT = 5  # 最多保留5个备份日志文件

# 不使用 basicConfig，避免自动添加 StreamHandler
logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False  # 防止日志传递到根日志器

# 创建 formatter 并设置到各处理器，确保文件也包含时间
formatter = logging.Formatter(LOG_FORMAT)

log_path: Path = Path.home() / ".aish" / "aish.log"

if not log_path.parent.exists():
    log_path.parent.mkdir(parents=True)

# 使用 RotatingFileHandler 实现按大小自动轮转
file_handler = RotatingFileHandler(
    log_path,
    encoding="utf-8",
    maxBytes=MAX_LOG_SIZE,
    backupCount=BACKUP_COUNT,
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
