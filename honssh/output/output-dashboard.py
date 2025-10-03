#!/usr/bin/env python3

# Copyright (c) 2025 Dashboard Integration
# HonSSH Dashboard Real-time Plugin

from honssh.config import Config
from honssh.utils import validation
from honssh import log

import datetime
import time
import json
import requests
from threading import Thread


class Plugin(object):
    """
    Dashboard plugin for real-time updates to HonSSH Dashboard
    Sends events via HTTP POST to the dashboard API
    """
    
    def __init__(self):
        self.cfg = Config.getInstance()
        self.dashboard_url = None
        self.enabled = False
        
    def start_server(self):
        """Initialize dashboard connection"""
        if self.cfg.getboolean(['output-dashboard', 'enabled']):
            self.enabled = True
            host = self.cfg.get(['output-dashboard', 'api_host'])
            port = self.cfg.get(['output-dashboard', 'api_port'])
            self.dashboard_url = f"http://{host}:{port}"
            log.msg(log.LGREEN, '[PLUGIN][DASHBOARD]', f'Dashboard integration enabled: {self.dashboard_url}')
        
    def set_server(self, server):
        """Set server reference"""
        pass
    
    def _send_event(self, event_type, data):
        """Send event to dashboard API asynchronously"""
        if not self.enabled:
            return
            
        def send():
            try:
                url = f"{self.dashboard_url}/api/events/{event_type}"
                response = requests.post(url, json=data, timeout=5)
                if response.status_code != 200:
                    log.msg(log.LYELLOW, '[PLUGIN][DASHBOARD]', 
                           f'Warning: Dashboard returned {response.status_code}')
            except requests.exceptions.ConnectionError:
                # Dashboard might not be running, fail silently
                pass
            except Exception as e:
                log.msg(log.LYELLOW, '[PLUGIN][DASHBOARD]', 
                       f'Error sending event: {str(e)}')
        
        # Send asynchronously to not block HonSSH
        thread = Thread(target=send)
        thread.daemon = True
        thread.start()
    
    def connection_made(self, sensor):
        """Called when a new connection is established"""
        session = sensor['session']
        self._send_event('connection_made', {
            'session_id': session['session_id'],
            'peer_ip': session['peer_ip'],
            'peer_port': session['peer_port'],
            'start_time': session['start_time'],
            'country': session.get('country', ''),
            'sensor_name': sensor['sensor_name']
        })
        log.msg(log.LBLUE, '[PLUGIN][DASHBOARD]', 
               f'New connection: {session["peer_ip"]}')
    
    def connection_lost(self, sensor):
        """Called when connection is closed"""
        session = sensor['session']
        self._send_event('connection_lost', {
            'session_id': session['session_id'],
            'peer_ip': session['peer_ip'],
            'end_time': session.get('end_time', ''),
            'start_time': session['start_time']
        })
    
    def set_client(self, sensor):
        """Called when client version is identified"""
        session = sensor['session']
        self._send_event('client_identified', {
            'session_id': session['session_id'],
            'version': session.get('version', 'Unknown'),
            'peer_ip': session['peer_ip']
        })
    
    def login_successful(self, sensor):
        """Called on successful authentication"""
        session = sensor['session']
        auth = session.get('auth', {})
        self._send_event('login_success', {
            'session_id': session['session_id'],
            'peer_ip': session['peer_ip'],
            'username': auth.get('username', ''),
            'password': auth.get('password', ''),
            'timestamp': auth.get('date_time', '')
        })
        log.msg(log.LGREEN, '[PLUGIN][DASHBOARD]', 
               f'Login successful: {auth.get("username", "")}@{session["peer_ip"]}')
    
    def login_failed(self, sensor):
        """Called on failed authentication"""
        session = sensor['session']
        auth = session.get('auth', {})
        self._send_event('login_failed', {
            'session_id': session['session_id'],
            'peer_ip': session['peer_ip'],
            'username': auth.get('username', ''),
            'password': auth.get('password', ''),
            'timestamp': auth.get('date_time', '')
        })
    
    def channel_opened(self, sensor):
        """Called when a channel is opened"""
        session = sensor['session']
        channel = session.get('channel', {})
        self._send_event('channel_opened', {
            'session_id': session['session_id'],
            'channel_id': channel.get('uuid', ''),
            'channel_type': channel.get('name', ''),
            'timestamp': channel.get('start_time', '')
        })
    
    def channel_closed(self, sensor):
        """Called when a channel is closed"""
        session = sensor['session']
        channel = session.get('channel', {})
        self._send_event('channel_closed', {
            'session_id': session['session_id'],
            'channel_id': channel.get('uuid', ''),
            'timestamp': channel.get('end_time', '')
        })
    
    def command_entered(self, sensor):
        """Called when a command is executed"""
        session = sensor['session']
        channel = session.get('channel', {})
        command = channel.get('command', {})
        
        self._send_event('command_executed', {
            'session_id': session['session_id'],
            'peer_ip': session['peer_ip'],
            'command': command.get('command', ''),
            'timestamp': command.get('date_time', ''),
            'blocked': command.get('blocked', False)
        })
        log.msg(log.LCYAN, '[PLUGIN][DASHBOARD]', 
               f'Command: {command.get("command", "")}')
    
    def download_started(self, sensor):
        """Called when file download starts"""
        session = sensor['session']
        channel = session.get('channel', {})
        download = channel.get('download', {})
        
        self._send_event('download_started', {
            'session_id': session['session_id'],
            'peer_ip': session['peer_ip'],
            'url': download.get('link', ''),
            'timestamp': download.get('start_time', '')
        })
    
    def download_finished(self, sensor):
        """Called when file download completes"""
        session = sensor['session']
        channel = session.get('channel', {})
        download = channel.get('download', {})
        
        self._send_event('download_completed', {
            'session_id': session['session_id'],
            'peer_ip': session['peer_ip'],
            'url': download.get('link', ''),
            'file': download.get('file', ''),
            'size': download.get('size', 0),
            'sha256': download.get('sha256', ''),
            'timestamp': download.get('start_time', '')
        })
        log.msg(log.LPURPLE, '[PLUGIN][DASHBOARD]', 
               f'Download: {download.get("link", "")}')
    
    def validate_config(self):
        """Validate plugin configuration"""
        props = [['output-dashboard', 'enabled']]
        for prop in props:
            if not self.cfg.check_exist(prop, validation.check_valid_boolean):
                return False
        
        # If enabled, validate required settings
        if self.cfg.getboolean(['output-dashboard', 'enabled']):
            required_props = [
                ['output-dashboard', 'api_host'],
                ['output-dashboard', 'api_port']
            ]
            for prop in required_props:
                if not self.cfg.check_exist(prop):
                    return False
        
        return True
