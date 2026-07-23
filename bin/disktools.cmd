@echo off
setlocal
set "PYTHONPATH=D:\Project\Utility-Maintenance-Disk;%PYTHONPATH%"
python -m disktools %*
