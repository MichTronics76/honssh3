# HonSSH3 Installation Guide

## Requirements

HonSSH3 requires Python 3.8 or higher. Tested with Python 3.12.3.

## Quick Start

### 1. Install System Dependencies

**Debian/Ubuntu:**
```bash
sudo apt-get update
sudo apt-get install python3-dev python3-venv libmysqlclient-dev build-essential
sudo apt-get install geoip-database geoip-database-extra  # Optional: for GeoIP
```

**RedHat/CentOS/Fedora:**
```bash
sudo yum install python3-devel mysql-devel gcc
sudo yum install GeoIP GeoIP-data  # Optional: for GeoIP
```

### 2. Create Virtual Environment

```bash
cd /path/to/honssh3
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate     # On Windows
```

### 3. Install Python Dependencies

**Full Installation (recommended):**
```bash
pip install -r requirements.txt
```

**Minimal Installation (no MySQL, no GeoIP):**
```bash
pip install -r requirements-minimal.txt
```

**Development Installation:**
```bash
pip install -r requirements-dev.txt
```

## Requirements Files

### `requirements.txt` (Production - Recommended)
Full installation with all features:
- Twisted 25.5.0 (SSH/networking)
- mysqlclient 2.2.7 (MySQL logging)
- GeoIP 1.3.2 (IP geolocation)
- watchdog 6.0.0 (file monitoring)
- bcrypt 5.0.0 (password hashing)
- cryptography 46.0.2 (SSH crypto)
- Docker support (optional, commented out)

### `requirements-minimal.txt` (Minimal)
Core functionality only:
- Twisted, watchdog, bcrypt, cryptography
- No MySQL, no GeoIP, no Docker
- Text file logging only

### `requirements-dev.txt` (Development)
Includes everything in requirements.txt plus:
- pytest, pytest-twisted (testing)
- black, flake8, pylint, mypy (code quality)
- Sphinx (documentation)
- ipython, ipdb (debugging)

### `requirements` (Deprecated)
Legacy file without version pinning. Use `requirements.txt` instead.

## Troubleshooting

### GeoIP Installation Fails

If `GeoIP==1.3.2` fails to install:

1. Edit `requirements.txt`
2. Comment out: `# GeoIP==1.3.2`
3. Uncomment: `pygeoip==0.3.2`
4. Run: `pip install -r requirements.txt`

The application will automatically fall back to pygeoip if GeoIP is unavailable.

### mysqlclient Installation Fails

**Error:** `mysql_config not found` or similar

**Solution:** Install MySQL development headers:
```bash
# Debian/Ubuntu
sudo apt-get install libmysqlclient-dev

# RedHat/CentOS
sudo yum install mysql-devel
```

### Docker Support

Docker support is optional and commented out by default. To enable:

1. Edit `requirements.txt`
2. Uncomment the docker lines:
   ```
   docker==7.1.0
   # docker-py==1.10.6  # Keep commented unless needed for legacy support
   ```
3. Run: `pip install -r requirements.txt`

**Note:** `docker` and `docker-py` can conflict. Use only `docker` unless you specifically need `docker-py` for backward compatibility.

### Cryptography Deprecation Warnings

You may see warnings like:
```
CryptographyDeprecationWarning: TripleDES has been moved to cryptography.hazmat.decrepit
```

This is **expected and harmless**. TripleDES support will be removed in cryptography 48.0.0, but HonSSH3 works fine with these warnings for now. The warnings come from Twisted's SSH implementation, not HonSSH3.

## Verifying Installation

After installation, verify dependencies:

```bash
source venv/bin/activate
pip check  # Should show "No broken requirements found"
python3 -c "import twisted; print(f'Twisted {twisted.__version__} OK')"
```

## Upgrading

To upgrade all dependencies to the latest versions:

```bash
source venv/bin/activate
pip install --upgrade -r requirements.txt
```

**Warning:** Upgrading may introduce breaking changes. Test thoroughly in a non-production environment first.

## Production Deployment

For production deployments:

1. Use `requirements.txt` with pinned versions
2. Create a separate virtual environment
3. Never run as root user
4. Use system service manager (systemd) for auto-start
5. Enable log rotation
6. Monitor disk space for session recordings

## Support

For issues related to:
- **HonSSH3:** https://github.com/MichTronics76/honssh3
- **Original HonSSH:** https://github.com/tnich/honssh
- **Twisted:** https://twisted.org/
- **Python:** https://www.python.org/

## License

See the LICENSE file in the repository root.
