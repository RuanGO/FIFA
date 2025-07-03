@echo off
REM --------------------------------------------------
REM  Script para apagar todos os .json de persistência
REM --------------------------------------------------

echo Deletando arquivos de persistência...
del /Q players.json
del /Q league_matches.json
del /Q league_results.json
del /Q brackets.json
del /Q knock_results.json
del /Q results.json

echo.
echo Todos os arquivos JSON foram removidos.
pause
