"""Exercise the dedicated kind namespace; retain one uniquely tagged test row."""
import json
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request


def main():
    kubeconfig, context, namespace = sys.argv[1:]
    command = ['kubectl', '--kubeconfig', kubeconfig, '--context', context,
               '--namespace', namespace]

    def kubectl(*args):
        return subprocess.check_output(command + list(args), text=True, timeout=180).strip()

    def request(path, data=None):
        with urllib.request.urlopen(base + path, data=data, timeout=15) as response:
            assert response.status == 200
            return response.read().decode()

    marker = 'kind-smoke-' + secrets.token_hex(12)
    with tempfile.TemporaryFile(mode='w+') as output:
        process = subprocess.Popen(command + ['port-forward', '--address', '127.0.0.1',
                                              'service/php', ':80'], stdout=output,
                                   stderr=subprocess.STDOUT, text=True)
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                output.seek(0)
                lines = output.read().splitlines()
                forwarding = next((line for line in lines if line.startswith('Forwarding from 127.0.0.1:')), None)
                if forwarding:
                    port = forwarding.split('127.0.0.1:')[1].split()[0]
                    break
                if process.poll() is not None:
                    raise RuntimeError('Port forwarding failed: ' + '\n'.join(lines))
                time.sleep(0.25)
            else:
                raise TimeoutError('Port forwarding did not become ready.')
            base = f'http://127.0.0.1:{port}'
            assert '<form' in request('/')
            assert request('/health.php').strip() == 'Ready'
            payload = urllib.parse.urlencode({'nome': 'Kind validation',
                                             'email': 'kind@example.com',
                                             'comentario': marker}).encode()
            assert request('/index.php', payload).strip() == 'New record created successfully'

            def row_count():
                return kubectl('exec', 'deployment/mysql', '--', 'sh', '-c',
                               'MYSQL_PWD="$MYSQL_PASSWORD" mysql --protocol=TCP '
                               '--host=127.0.0.1 --user="$MYSQL_USER" --database="$MYSQL_DATABASE" '
                               f'--batch --skip-column-names --execute="SELECT COUNT(*) FROM mensagens WHERE comentario=\'{marker}\'"')

            assert row_count() == '1', 'Submitted message was not stored.'
            pvc = json.loads(kubectl('get', 'pvc', 'mysql-dados', '-o', 'json'))
            assert pvc['status']['phase'] == 'Bound', 'PVC is not bound.'
            old = json.loads(kubectl('get', 'pods', '-l', 'app=mysql', '-o', 'json'))['items'][0]
            kubectl('delete', 'pod', old['metadata']['name'], '--wait=true', '--timeout=120s')
            deadline = time.monotonic() + 150
            while time.monotonic() < deadline:
                pods = json.loads(kubectl('get', 'pods', '-l', 'app=mysql', '-o', 'json'))['items']
                if any(p['metadata']['uid'] != old['metadata']['uid'] and
                       any(c['type'] == 'Ready' and c['status'] == 'True'
                           for c in p.get('status', {}).get('conditions', [])) for p in pods):
                    break
                time.sleep(2)
            else:
                raise TimeoutError('Replacement MySQL pod did not become ready.')
            assert row_count() == '1', 'Message did not survive MySQL pod replacement.'
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline:
                try:
                    if request('/health.php').strip() == 'Ready':
                        break
                except (OSError, TimeoutError):
                    pass
                time.sleep(2)
            else:
                raise TimeoutError('Application readiness did not recover.')
            print('PASS: form, readiness, submission, bound PVC, MySQL pod replacement and persistence.')
            print('One smoke-test message remains in the local database: ' + marker)
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == '__main__':
    main()
