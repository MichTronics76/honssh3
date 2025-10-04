#!/usr/bin/env python3
"""
HonSSH Dashboard API
Professional REST API for HonSSH monitoring and analytics
"""

from flask import Flask, jsonify, request, send_from_directory, abort
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import MySQLdb
import MySQLdb.cursors
import datetime
import time
import os
import sys
import configparser
import math
from collections import Counter, defaultdict
from dateutil import parser as date_parser

# Add parent directory to path to import honssh modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

APP_ROOT = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'honssh-dashboard-secret-key-change-this'
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Configuration
CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'honssh.cfg')
if not os.path.exists(CONFIG_FILE):
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'honssh.cfg.default')

config = configparser.ConfigParser()
config.read(CONFIG_FILE)


@app.route('/')
def serve_dashboard():
    """Serve the dashboard single-page application."""
    return send_from_directory(APP_ROOT, 'index.html')


@app.route('/<path:filename>')
def serve_static_asset(filename):
    """Serve additional static assets while keeping /api namespace reserved."""
    if filename.startswith('api/'):
        abort(404)

    file_path = os.path.join(APP_ROOT, filename)
    if os.path.isfile(file_path):
        return send_from_directory(APP_ROOT, filename)

    abort(404)


def get_db_connection():
    """Create database connection"""
    try:
        db = MySQLdb.connect(
            host=config.get('output-mysql', 'host'),
            db=config.get('output-mysql', 'database'),
            user=config.get('output-mysql', 'username'),
            passwd=config.get('output-mysql', 'password'),
            port=int(config.get('output-mysql', 'port')),
            cursorclass=MySQLdb.cursors.DictCursor
        )
        return db
    except Exception as e:
        print(f"Database connection error: {e}")
        return None


def execute_query(query, params=None):
    """Execute query and return results"""
    db = get_db_connection()
    if not db:
        return []
    
    try:
        cursor = db.cursor()
        cursor.execute(query, params or ())
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"Query error: {e}")
        return []
    finally:
        db.close()


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    db = get_db_connection()
    if db:
        db.close()
        return jsonify({'status': 'healthy', 'database': 'connected'})
    return jsonify({'status': 'unhealthy', 'database': 'disconnected'}), 500


@app.route('/api/stats/overview', methods=['GET'])
def get_overview_stats():
    """Get overview statistics"""
    try:
        # Total sessions
        total_sessions = execute_query("SELECT COUNT(*) as count FROM sessions")[0]['count']
        
        # Active sessions (no end time)
        active_sessions = execute_query("SELECT COUNT(*) as count FROM sessions WHERE endtime IS NULL")[0]['count']
        
        # Total authentication attempts
        total_auth = execute_query("SELECT COUNT(*) as count FROM auth")[0]['count']
        
        # Successful logins
        successful_auth = execute_query("SELECT COUNT(*) as count FROM auth WHERE success = 1")[0]['count']
        
        # Total commands
        total_commands = execute_query("SELECT COUNT(*) as count FROM commands")[0]['count']
        
        # Total downloads
        total_downloads = execute_query("SELECT COUNT(*) as count FROM downloads")[0]['count']
        
        # Unique IPs
        unique_ips = execute_query("SELECT COUNT(DISTINCT ip) as count FROM sessions")[0]['count']
        
        # Unique usernames tried
        unique_usernames = execute_query("SELECT COUNT(DISTINCT username) as count FROM auth")[0]['count']
        
        return jsonify({
            'total_sessions': total_sessions,
            'active_sessions': active_sessions,
            'total_auth_attempts': total_auth,
            'successful_logins': successful_auth,
            'failed_logins': total_auth - successful_auth,
            'total_commands': total_commands,
            'total_downloads': total_downloads,
            'unique_ips': unique_ips,
            'unique_usernames': unique_usernames,
            'success_rate': round((successful_auth / total_auth * 100) if total_auth > 0 else 0, 2)
        })
    except Exception as e:
        print(f"Error in overview stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sessions/recent', methods=['GET'])
def get_recent_sessions():
    """Get recent sessions"""
    limit = request.args.get('limit', 50, type=int)
    
    query = """
        SELECT s.id, s.starttime, s.endtime, s.ip, s.port, 
               sen.name as sensor_name, sen.ip as sensor_ip,
               c.version as client_version,
               TIMESTAMPDIFF(SECOND, s.starttime, COALESCE(s.endtime, NOW())) as duration
        FROM sessions s
        LEFT JOIN sensors sen ON s.sensor = sen.id
        LEFT JOIN clients c ON s.client = c.id
        ORDER BY s.starttime DESC
        LIMIT %s
    """
    
    sessions = execute_query(query, (limit,))
    
    # Format dates for JSON
    for session in sessions:
        if session['starttime']:
            session['starttime'] = session['starttime'].strftime('%Y-%m-%d %H:%M:%S')
        if session['endtime']:
            session['endtime'] = session['endtime'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(sessions)


@app.route('/api/sessions/active', methods=['GET'])
def get_active_sessions():
    """Get currently active sessions"""
    query = """
        SELECT s.id, s.starttime, s.ip, s.port, 
               sen.name as sensor_name,
               c.version as client_version,
               TIMESTAMPDIFF(SECOND, s.starttime, NOW()) as duration
        FROM sessions s
        LEFT JOIN sensors sen ON s.sensor = sen.id
        LEFT JOIN clients c ON s.client = c.id
        WHERE s.endtime IS NULL
        ORDER BY s.starttime DESC
    """
    
    sessions = execute_query(query)
    
    for session in sessions:
        if session['starttime']:
            session['starttime'] = session['starttime'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(sessions)


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session_details(session_id):
    """Get detailed information about a specific session"""
    # Session info
    session_query = """
        SELECT s.*, sen.name as sensor_name, sen.ip as sensor_ip, sen.port as sensor_port,
               c.version as client_version
        FROM sessions s
        LEFT JOIN sensors sen ON s.sensor = sen.id
        LEFT JOIN clients c ON s.client = c.id
        WHERE s.id = %s
    """
    session = execute_query(session_query, (session_id,))
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    
    session = session[0]
    
    # Get authentication attempts
    auth_query = """
        SELECT timestamp, username, password, success, ip, country
        FROM auth
        WHERE timestamp >= %s AND timestamp <= COALESCE(%s, NOW())
        ORDER BY timestamp
    """
    auths = execute_query(auth_query, (session['starttime'], session['endtime']))
    
    # Get channels
    channel_query = """
        SELECT id, type, starttime, endtime
        FROM channels
        WHERE sessionid = %s
        ORDER BY starttime
    """
    channels = execute_query(channel_query, (session_id,))
    
    # Get commands
    command_query = """
        SELECT c.timestamp, c.command, ch.type as channel_type
        FROM commands c
        JOIN channels ch ON c.channelid = ch.id
        WHERE ch.sessionid = %s
        ORDER BY c.timestamp
    """
    commands = execute_query(command_query, (session_id,))
    
    # Get downloads
    download_query = """
        SELECT d.timestamp, d.url, d.outfile
        FROM downloads d
        JOIN channels ch ON d.channelid = ch.id
        WHERE ch.sessionid = %s
        ORDER BY d.timestamp
    """
    downloads = execute_query(download_query, (session_id,))
    
    # Format dates
    if session['starttime']:
        session['starttime'] = session['starttime'].strftime('%Y-%m-%d %H:%M:%S')
    if session['endtime']:
        session['endtime'] = session['endtime'].strftime('%Y-%m-%d %H:%M:%S')
    
    for auth in auths:
        auth['timestamp'] = auth['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    
    for channel in channels:
        channel['starttime'] = channel['starttime'].strftime('%Y-%m-%d %H:%M:%S')
        if channel['endtime']:
            channel['endtime'] = channel['endtime'].strftime('%Y-%m-%d %H:%M:%S')
    
    for cmd in commands:
        cmd['timestamp'] = cmd['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    
    for dl in downloads:
        dl['timestamp'] = dl['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify({
        'session': session,
        'authentications': auths,
        'channels': channels,
        'commands': commands,
        'downloads': downloads
    })


@app.route('/api/auth/attempts', methods=['GET'])
def get_auth_attempts():
    """Get authentication attempts"""
    limit = request.args.get('limit', 100, type=int)
    success = request.args.get('success', None)
    
    query = "SELECT timestamp, username, password, success, ip, country FROM auth"
    params = []
    
    if success is not None:
        query += " WHERE success = %s"
        params.append(1 if success == 'true' else 0)
    
    query += " ORDER BY timestamp DESC LIMIT %s"
    params.append(limit)
    
    attempts = execute_query(query, tuple(params))
    
    for attempt in attempts:
        attempt['timestamp'] = attempt['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(attempts)


@app.route('/api/auth/top-usernames', methods=['GET'])
def get_top_usernames():
    """Get most used usernames"""
    limit = request.args.get('limit', 20, type=int)
    
    query = """
        SELECT username, COUNT(*) as count, 
               SUM(success) as successful,
               COUNT(*) - SUM(success) as failed
        FROM auth
        GROUP BY username
        ORDER BY count DESC
        LIMIT %s
    """
    
    return jsonify(execute_query(query, (limit,)))


@app.route('/api/auth/top-passwords', methods=['GET'])
def get_top_passwords():
    """Get most used passwords"""
    limit = request.args.get('limit', 20, type=int)
    
    query = """
        SELECT password, COUNT(*) as count,
               SUM(success) as successful,
               COUNT(*) - SUM(success) as failed
        FROM auth
        GROUP BY password
        ORDER BY count DESC
        LIMIT %s
    """
    
    return jsonify(execute_query(query, (limit,)))


@app.route('/api/auth/top-combinations', methods=['GET'])
def get_top_combinations():
    """Get most used username/password combinations"""
    limit = request.args.get('limit', 20, type=int)
    
    query = """
        SELECT username, password, COUNT(*) as count,
               SUM(success) as successful
        FROM auth
        GROUP BY username, password
        ORDER BY count DESC
        LIMIT %s
    """
    
    return jsonify(execute_query(query, (limit,)))


@app.route('/api/auth/top-countries', methods=['GET'])
def get_top_countries():
    """Get authentication activity aggregated by country."""
    limit = request.args.get('limit', 10, type=int)

    query = """
        SELECT
            CASE
                WHEN country IS NULL OR country = '' THEN 'Unknown'
                ELSE country
            END AS country,
            COUNT(*) AS attempts,
            SUM(success) AS successful,
            COUNT(*) - SUM(success) AS failed
        FROM auth
        GROUP BY country
        ORDER BY attempts DESC
        LIMIT %s
    """

    return jsonify(execute_query(query, (limit,)))


@app.route('/api/auth/top-ips', methods=['GET'])
def get_top_ips():
    """Get authentication activity aggregated by source IP."""
    limit = request.args.get('limit', 10, type=int)

    query = """
        SELECT
            ip,
            COUNT(*) AS attempts,
            SUM(success) AS successful,
            COUNT(*) - SUM(success) AS failed,
            MAX(timestamp) AS last_seen
        FROM auth
        GROUP BY ip
        ORDER BY attempts DESC
        LIMIT %s
    """

    results = execute_query(query, (limit,))

    for row in results:
        if row['last_seen']:
            row['last_seen'] = row['last_seen'].strftime('%Y-%m-%d %H:%M:%S')

    return jsonify(results)


@app.route('/api/commands/recent', methods=['GET'])
def get_recent_commands():
    """Get recent commands"""
    limit = request.args.get('limit', 100, type=int)
    
    query = """
        SELECT c.timestamp, c.command, ch.type as channel_type, s.ip as source_ip
        FROM commands c
        JOIN channels ch ON c.channelid = ch.id
        JOIN sessions s ON ch.sessionid = s.id
        ORDER BY c.timestamp DESC
        LIMIT %s
    """
    
    commands = execute_query(query, (limit,))
    
    for cmd in commands:
        cmd['timestamp'] = cmd['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(commands)


@app.route('/api/commands/top', methods=['GET'])
def get_top_commands():
    """Get most executed commands"""
    limit = request.args.get('limit', 20, type=int)
    
    query = """
        SELECT command, COUNT(*) as count
        FROM commands
        GROUP BY command
        ORDER BY count DESC
        LIMIT %s
    """
    
    return jsonify(execute_query(query, (limit,)))


@app.route('/api/attackers/top', methods=['GET'])
def get_top_attackers():
    """Get top attacking IPs"""
    limit = request.args.get('limit', 20, type=int)
    
    query = """
        SELECT ip, COUNT(*) as session_count,
               MIN(starttime) as first_seen,
               MAX(starttime) as last_seen
        FROM sessions
        GROUP BY ip
        ORDER BY session_count DESC
        LIMIT %s
    """
    
    attackers = execute_query(query, (limit,))
    
    for attacker in attackers:
        if attacker['first_seen']:
            attacker['first_seen'] = attacker['first_seen'].strftime('%Y-%m-%d %H:%M:%S')
        if attacker['last_seen']:
            attacker['last_seen'] = attacker['last_seen'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(attackers)


@app.route('/api/downloads/recent', methods=['GET'])
def get_recent_downloads():
    """Get recent file downloads"""
    limit = request.args.get('limit', 50, type=int)
    
    query = """
        SELECT d.timestamp, d.url, d.outfile, s.ip as source_ip
        FROM downloads d
        JOIN channels ch ON d.channelid = ch.id
        JOIN sessions s ON ch.sessionid = s.id
        ORDER BY d.timestamp DESC
        LIMIT %s
    """
    
    downloads = execute_query(query, (limit,))
    
    for dl in downloads:
        dl['timestamp'] = dl['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
    
    return jsonify(downloads)


@app.route('/api/stats/timeline', methods=['GET'])
def get_timeline_stats():
    """Get timeline statistics"""
    days = request.args.get('days', 7, type=int)
    
    query = """
        SELECT DATE(starttime) as date,
               COUNT(*) as sessions,
               COUNT(DISTINCT ip) as unique_ips
        FROM sessions
        WHERE starttime >= DATE_SUB(NOW(), INTERVAL %s DAY)
        GROUP BY DATE(starttime)
        ORDER BY date
    """
    
    timeline = execute_query(query, (days,))
    
    for entry in timeline:
        entry['date'] = entry['date'].strftime('%Y-%m-%d')
    
    return jsonify(timeline)


@app.route('/api/stats/hourly', methods=['GET'])
def get_hourly_stats():
    """Get hourly statistics for the last 24 hours"""
    query = """
        SELECT HOUR(starttime) as hour, COUNT(*) as sessions
        FROM sessions
        WHERE starttime >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        GROUP BY HOUR(starttime)
        ORDER BY hour
    """
    
    return jsonify(execute_query(query))


@app.route('/api/auth/timeline', methods=['GET'])
def get_auth_timeline():
    """Get authentication attempts grouped into fixed windows for the last 24 hours."""
    window_hours = request.args.get('window_hours', 2, type=int)
    total_hours = request.args.get('total_hours', 24, type=int)

    # Clamp to sensible ranges to avoid excessive load or invalid intervals
    window_hours = max(1, min(window_hours, 12))
    total_hours = max(window_hours, min(total_hours, 168))

    window_seconds = window_hours * 3600
    bucket_count = math.ceil(total_hours / window_hours)
    total_span_hours = bucket_count * window_hours

    raw_data = execute_query(
        """
        SELECT FROM_UNIXTIME(FLOOR(UNIX_TIMESTAMP(timestamp) / %s) * %s) AS window_start,
               COUNT(*) AS attempts,
               SUM(success) AS successes
        FROM auth
        WHERE timestamp >= DATE_SUB(NOW(), INTERVAL %s HOUR)
        GROUP BY window_start
        ORDER BY window_start
        """,
        (window_seconds, window_seconds, total_span_hours)
    )

    bucket_map = {}
    for row in raw_data:
        if not row['window_start']:
            continue
        bucket_map[row['window_start']] = {
            'attempts': int(row['attempts'] or 0),
            'successes': int(row['successes'] or 0)
        }

    now = datetime.datetime.now()
    bucket_size = datetime.timedelta(seconds=window_seconds)
    current_bucket_end = (
        math.floor(now.timestamp() / window_seconds) * window_seconds
    ) + window_seconds
    start_timestamp = current_bucket_end - (bucket_count * window_seconds)

    timeline = []
    for i in range(bucket_count):
        bucket_start_ts = start_timestamp + (i * window_seconds)
        bucket_start = datetime.datetime.fromtimestamp(bucket_start_ts)
        bucket_end = bucket_start + bucket_size

        bucket_stats = bucket_map.get(bucket_start, {'attempts': 0, 'successes': 0})
        attempts = bucket_stats['attempts']
        successes = bucket_stats['successes']
        failures = max(0, attempts - successes)

        timeline.append({
            'window_start': bucket_start.strftime('%Y-%m-%d %H:%M:%S'),
            'window_end': bucket_end.strftime('%Y-%m-%d %H:%M:%S'),
            'attempts': attempts,
            'successes': successes,
            'failures': failures
        })

    return jsonify(timeline)


@app.route('/api/sensors/list', methods=['GET'])
def get_sensors():
    """Get all sensors"""
    query = """
        SELECT s.id, s.name, s.ip, s.port,
               COUNT(sess.id) as total_sessions,
               COUNT(CASE WHEN sess.endtime IS NULL THEN 1 END) as active_sessions
        FROM sensors s
        LEFT JOIN sessions sess ON s.id = sess.sensor
        GROUP BY s.id, s.name, s.ip, s.port
        ORDER BY s.name
    """
    
    return jsonify(execute_query(query))


@app.route('/api/clients/versions', methods=['GET'])
def get_client_versions():
    """Get SSH client version statistics"""
    query = """
        SELECT c.version, COUNT(*) as count
        FROM sessions s
        JOIN clients c ON s.client = c.id
        GROUP BY c.version
        ORDER BY count DESC
    """
    
    return jsonify(execute_query(query))


# WebSocket events for real-time updates
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print('Client connected')
    emit('connected', {'status': 'connected'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print('Client disconnected')


@socketio.on('subscribe')
def handle_subscribe(data):
    """Handle subscription to real-time updates"""
    print(f"Client subscribed to: {data}")
    emit('subscribed', {'status': 'subscribed', 'channel': data})


def broadcast_new_session(session_data):
    """Broadcast new session to all connected clients"""
    socketio.emit('new_session', session_data)


def broadcast_new_auth(auth_data):
    """Broadcast new authentication attempt to all connected clients"""
    socketio.emit('new_auth', auth_data)


def broadcast_new_command(command_data):
    """Broadcast new command to all connected clients"""
    socketio.emit('new_command', command_data)


if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         HonSSH Dashboard API Server                       ║
    ║         Professional Monitoring & Analytics               ║
    ╚═══════════════════════════════════════════════════════════╝
    
    Starting server on http://0.0.0.0:5000
    API Documentation: http://0.0.0.0:5000/api/health
    """)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
