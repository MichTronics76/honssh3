# HonSSH3 Requirements - Quick Reference

## Installation Commands

```bash
# Standard installation (recommended)
pip install -r requirements.txt

# Minimal installation (no MySQL/GeoIP/Docker)
pip install -r requirements-minimal.txt

# Development installation (includes testing tools)
pip install -r requirements-dev.txt
```

## Requirements Files Comparison

| File | Size | Packages | Use Case |
|------|------|----------|----------|
| `requirements.txt` | 3.8KB | 6 core + optional | Production (recommended) |
| `requirements-minimal.txt` | 633B | 4 core only | Lightweight/testing |
| `requirements-dev.txt` | 570B | All + dev tools | Development |
| `requirements` | 353B | Unpinned (deprecated) | Legacy compatibility |

## Core Dependencies (Always Required)

```
Twisted==25.5.0         # SSH/networking framework
watchdog==6.0.0         # File system monitoring
bcrypt==5.0.0           # Password hashing
cryptography==46.0.2    # SSH cryptography
```

## Optional Dependencies

```
mysqlclient==2.2.7      # MySQL database logging
GeoIP==1.3.2            # IP geolocation (or pygeoip==0.3.2)
docker==7.1.0           # Docker honeypot support
```

## System Prerequisites

**Debian/Ubuntu:**
```bash
sudo apt-get install python3-dev libmysqlclient-dev build-essential
```

**RedHat/CentOS:**
```bash
sudo yum install python3-devel mysql-devel gcc
```

## Common Issues & Fixes

### Issue: GeoIP won't install
**Fix:** Edit requirements.txt, comment GeoIP, uncomment pygeoip

### Issue: mysqlclient fails  
**Fix:** Install libmysqlclient-dev or mysql-devel first

### Issue: Permission denied
**Fix:** Use virtual environment, don't use sudo with pip

## Verification

```bash
# Check for conflicts
pip check

# List installed versions
pip list | grep -iE "twisted|mysql|geoip|watchdog|bcrypt|crypto|docker"

# Test import
python3 -c "import twisted; print('OK')"
```

## Documentation

- Full guide: `INSTALL.md`
- Summary: `REQUIREMENTS-SUMMARY.md`
- This card: `REQUIREMENTS-QUICK.md`

## Support

GitHub: https://github.com/MichTronics76/honssh3/issues
