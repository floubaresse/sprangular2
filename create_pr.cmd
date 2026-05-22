@echo off
for /f %%i in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%i
gh workflow run create_pr.yml --ref %BRANCH%
