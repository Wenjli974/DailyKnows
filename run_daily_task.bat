@echo off
echo 开始执行每日新闻简报任务 - %date% %time% >> task_execution.log
cd /d "%~dp0"
python main.py >> task_execution.log 2>&1
echo 任务执行完成 - %date% %time% >> task_execution.log
echo ---------------------------------------- >> task_execution.log 