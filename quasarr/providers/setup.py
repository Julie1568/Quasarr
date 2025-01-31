# -*- coding: utf-8 -*-
# Quasarr
# Project by https://github.com/rix1337

import os
import sys
from urllib import parse

from bottle import Bottle, request

import quasarr
from quasarr.downloads.sources import nx
from quasarr.persistence.config import Config
from quasarr.providers.html_templates import render_button, render_form, render_success, render_fail
from quasarr.providers.web_server import Server


def path_config(shared_state):
    app = Bottle()

    current_path = os.path.dirname(os.path.abspath(sys.argv[0]))

    @app.get('/')
    def config_form():
        config_form_html = f'''
            <form action="/api/config" method="post">
                <label for="config_path">Path</label><br>
                <input type="text" id="config_path" name="config_path" placeholder="{current_path}"><br>
                {render_button("Save", "primary", {"type": "submit"})}
            </form>
            '''
        return render_form("Press 'Save' to set desired path for configuration",
                           config_form_html)

    def set_config_path(config_path):
        config_path_file = "Quasarr.conf"

        if not config_path:
            config_path = current_path

        config_path = config_path.replace("\\", "/")
        config_path = config_path[:-1] if config_path.endswith('/') else config_path

        if not os.path.exists(config_path):
            os.makedirs(config_path)

        with open(config_path_file, "w") as f:
            f.write(config_path)

        return config_path

    @app.post("/api/config")
    def set_config():
        config_path = request.forms.get("config_path")
        config_path = set_config_path(config_path)
        quasarr.providers.web_server.temp_server_success = True
        return render_success(f'Config path set to: "{config_path}"',
                              5)

    print(f'Starting web server for config at: "{shared_state.values['external_address']}".')
    print("Please set desired config path there!")
    return Server(app, listen='0.0.0.0', port=shared_state.values['port']).serve_temporarily()


def hostnames_config(shared_state):
    app = Bottle()

    @app.get('/')
    def hostname_form():
        hostname_fields = '''
        <label for="{id}">{label}</label><br>
        <input type="text" id="{id}" name="{id}" placeholder="example.com"><br>
        '''

        hostname_form_content = "".join(
            [hostname_fields.format(id=label.lower(), label=label) for label in shared_state.values["sites"]])  # todo

        hostname_form_html = f'''
        <form action="/api/hostnames" method="post">
            {hostname_form_content}
            {render_button("Save", "primary", {"type": "submit"})}
        </form>
        '''

        return render_form("Set at least one valid hostname", hostname_form_html)

    @app.post("/api/hostnames")
    def set_hostnames():
        def extract_domain(url, shorthand):
            # Check if both characters from the shorthand appear in the url
            try:
                if '://' not in url:
                    url = 'http://' + url
                result = parse.urlparse(url)
                domain = result.netloc

                # Check if both characters in the shorthand are in the domain
                if all(char in domain for char in shorthand):
                    print(f"{domain} matches both characters from {shorthand}. Continuing...")
                    return domain
                else:
                    print(f"Invalid domain {domain}: Does not contain both characters from shorthand {shorthand}")
                    return None
            except Exception as e:
                print(f"Error parsing URL {url}: {e}")
                return None

        hostnames = Config('Hostnames')

        hostname_set = False

        for key in shared_state.values["sites"]:
            shorthand = key.lower()
            hostname = request.forms.get(shorthand)
            try:
                if hostname:
                    hostname = extract_domain(hostname, shorthand)
            except Exception as e:
                print(f"Error extracting domain from {hostname}: {e}")
                continue

            if hostname:
                hostnames.save(key, hostname)
                hostname_set = True

        if hostname_set:
            quasarr.providers.web_server.temp_server_success = True
            return render_success("At least one valid hostname set",
                                  5)
        else:
            return render_fail("No valid hostname provided!")

    print(
        f'Hostnames not set. Starting web server for config at: "{shared_state.values['external_address']}".')
    print("Please set at least one valid hostname there!")
    return Server(app, listen='0.0.0.0', port=shared_state.values['port']).serve_temporarily()


def nx_credentials_config(shared_state):
    app = Bottle()

    @app.get('/')
    def nx_credentials_form():
        form_content = '''
        <label for="user">Username</label><br>
        <input type="text" id="user" name="user" placeholder="user"><br>

        <label for="password">Password</label><br>
        <input type="password" id="password" name="password" placeholder="Password"><br>
        '''

        form_html = f'''
        <form action="/api/nx_credentials" method="post">
            {form_content}
            {render_button("Save", "primary", {"type": "submit"})}
        </form>
        '''

        return render_form("Set User and Password for NX", form_html)

    @app.post("/api/nx_credentials")
    def set_nx_credentials():
        user = request.forms.get('user')
        password = request.forms.get('password')
        nx_config = Config("NX")

        if user and password:
            nx_config.save("user", user)
            nx_config.save("password", password)

            if nx.create_and_persist_session(shared_state):
                quasarr.providers.web_server.temp_server_success = True
                return render_success("NX credentials set successfully", 5)

        nx_config.save("user", "")
        nx_config.save("password", "")
        return render_fail("User and Password wrong or empty!")

    print(
        f'NX credentials required to decrypt download links.'
        f'Starting web server for config at: "{shared_state.values['external_address']}".')
    print("Please set your NX user and password there! First register an account if you don't have one yet.")
    return Server(app, listen='0.0.0.0', port=shared_state.values['port']).serve_temporarily()


def jdownloader_config(shared_state):
    app = Bottle()

    @app.get('/')
    def hostname_form():
        verify_form_html = f'''
        <form id="verifyForm" action="/api/verify_jdownloader" method="post">
            <label for="user">E-Mail</label><br>
            <input type="text" id="user" name="user" placeholder="user@example.org"><br>
            <label for="pass">Password</label><br>
            <input type="password" id="pass" name="pass" placeholder="Password"><br>
            {render_button("Verify Credentials",
                           "secondary",
                           {"id": "verifyButton", "type": "button", "onclick": "verifyCredentials()"})}
        </form>
        <form action="/api/store_jdownloader" method="post" id="deviceForm" style="display: none;">
            <input type="hidden" id="hiddenUser" name="user">
            <input type="hidden" id="hiddenPass" name="pass">
            <label for="device">JDownloader</label><br>
            <select id="device" name="device"></select><br>
            {render_button("Save", "primary", {"type": "submit"})}
        </form>
        '''

        verify_script = '''
        <script>
        function verifyCredentials() {
            var user = document.getElementById('user').value;
            var pass = document.getElementById('pass').value;
            fetch('/api/verify_jdownloader', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({user: user, pass: pass}),
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    var select = document.getElementById('device');
                    data.devices.forEach(device => {
                        var opt = document.createElement('option');
                        opt.value = device;
                        opt.innerHTML = device;
                        select.appendChild(opt);
                    });
                    document.getElementById('hiddenUser').value = document.getElementById('user').value;
                    document.getElementById('hiddenPass').value = document.getElementById('pass').value;
                    document.getElementById("verifyButton").style.display = "none";
                    document.getElementById('deviceForm').style.display = 'block';
                } else {
                    alert('Fehler! Bitte die Zugangsdaten überprüfen.');
                }
            })
            .catch((error) => {
                console.error('Error:', error);
            });
        }
        </script>
        '''
        return render_form("Set your credentials from my.jdownloader.org", verify_form_html, verify_script)

    @app.post("/api/verify_jdownloader")
    def verify_jdownloader():
        data = request.json
        username = data['user']
        password = data['pass']

        devices = shared_state.get_devices(username, password)
        device_names = []

        if devices:
            for device in devices:
                device_names.append(device['name'])

        if device_names:
            return {"success": True, "devices": device_names}
        else:
            return {"success": False}

    @app.post("/api/store_jdownloader")
    def store_jdownloader():
        username = request.forms.get('user')
        password = request.forms.get('pass')
        device = request.forms.get('device')

        config = Config('JDownloader')

        if username and password and device:
            config.save('user', username)
            config.save('password', password)
            config.save('device', device)

            if not shared_state.set_device_from_config():
                config.save('user', "")
                config.save('password', "")
                config.save('device', "")
            else:
                quasarr.providers.web_server.temp_server_success = True
                return render_success("Credentials set",
                                      15)

        return render_fail("Could not set credentials!")

    print(
        f'My-JDownloader-Credentials not set. '
        f'Starting web server for config at: "{shared_state.values['external_address']}".')
    print("Please set your Credentials there!")
    return Server(app, listen='0.0.0.0', port=shared_state.values['port']).serve_temporarily()
