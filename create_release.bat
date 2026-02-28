@echo off
set VERSION=v1.0.1

echo Creating release %VERSION%...
echo.

git add .
git commit -m "Add HACS branding icons"
git push origin main

git tag -a %VERSION% -m "Release %VERSION% - Add HACS branding icons"
git push origin %VERSION%

echo.
echo Tag pushed! Now create release on GitHub:
echo https://github.com/lmt-lv/lmt-iot-ha-integration/releases/new?tag=%VERSION%
echo.
echo Release notes:
echo ## What's Changed
echo - Add HACS branding icons for better integration visibility
pause
