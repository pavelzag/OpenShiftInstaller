import paramiko
import os, pexpect
from configuration import *
from subprocess import call


port = 22


def main():

    default_user = get_machine_config('master').get('USER')
    default_pass = get_machine_config('master').get('PASS')
    master_ip = get_machine_config('master').get('IP')
    nodes_list = machines_names()
    nodes_ips = []
    for node in nodes_list:
        ip = get_machine_config(node).get('IP')
        print(ip)
        nodes_ips.append(ip)
    nodes_ips.append(master_ip)
    # Passwordless commands
    # For master :
    password_less(command='ssh-keygen', machine=master_ip, username=default_user, password=default_pass)
    password_less(command='ssh-copy-id', machine=master_ip, username=default_user, password=default_pass)
    # For nodes:
    for ip in nodes_ips:
        password_less(command='ssh-keygen', machine=ip, username=default_user, password=default_pass)
        password_less(command='ssh-copy-id', machine=ip, username=default_user, password=default_pass)
    node_params = []
    for node in nodes_list:
        node_params.append(get_machine_config(node))
    for i in xrange(0,len(node_params)):
        subscription_ip = node_params[i]['IP']
        print('Preparing subscriptions and installations on ' + subscription_ip)
        username = node_params[i]['USER']
        password = node_params[i]['PASS']
        # Subscription Commands
        sub_command(command='subscribe', machine=subscription_ip, username=username, password=password)
        sub_command(command='attach', machine=subscription_ip, username=username, password=password)
        sub_command(command='disabling', machine=subscription_ip, username=username, password=password)
        sub_command(command='enabling', machine=subscription_ip, username=username, password=password)
        # Installation Commands
        installation_command(command='install-tools', machine=subscription_ip, username=username, password=password)
        installation_command(command='update', machine=subscription_ip, username=username, password=password)
        installation_command(command='install-openshift', machine=subscription_ip, username=username, password=password)
        installation_command(command='excluder', machine=subscription_ip, username=username, password=password)
        installation_command(command='unexcluder', machine=subscription_ip, username=username, password=password)
    print('Shit worked')


def sub_command(command, machine, username, password):
    if command == 'subscribe':
        command = 'subscription-manager register --username=qa@redhat.com --password=' + get_creds().get('qe_pass')
    elif command == 'attach':
        command = 'subscription-manager attach --pool=8a85f9823e3d5e43013e3ddd4e2a0977'
    elif command == 'disabling':
        command = 'subscription-manager repos --disable="*"'
    elif command == 'enabling':
        command = 'subscription-manager repos \
    --enable="rhel-7-server-rpms" \
    --enable="rhel-7-server-extras-rpms" \
    --enable="rhel-7-server-ose-3.5-rpms" \
    --enable="rhel-7-fast-datapath-rpms"'
    status = run_command(command=command, hostname=machine, usernrame=username, password=password)
    if status == 0:
        print(command + ' for ' + str(machine) + ' was successful')
    else:
        print(command + ' for ' + str(machine) + ' has failed')
    return


def installation_command(command, machine, username, password):
    if command == 'install-tools':
        command = 'yum install wget git net-tools bind-utils iptables-services bridge-utils bash-completion -y'
    elif command == 'update':
        command = 'yum update -y'
    elif command == 'install-openshift':
        command = 'yum install atomic-openshift-utils -y'
    elif command == 'excluder':
        command = 'yum install atomic-openshift-excluder atomic-openshift-docker-excluder -y'
    elif command == 'unexcluder':
        command = 'atomic-openshift-excluder unexclude'
    print('Running installation of ' + command + '. This may take a few minutes. Get some coffee')
    status = run_command(command=command, hostname=machine, username=username, password=password)
    if status == 0:
        print(command + ' for ' + str(machine) + ' was successful')
    else:
        print(command + ' for ' + str(machine) + ' has failed')
    return


def password_less(command, machine, username, password, nodes_ips=None):
    if command == 'ssh-keygen':
        command = 'ssh-keygen -f /root/.ssh/id_rsa -t rsa -N ""'
    elif command == 'ssh-copy-id':
        if not nodes_ips:
            cert_path = copy_id_to_local(hostname=machine, username=username, password=password)
            sshcopy = SshCopy(user=username, host=machine, passwd=password, port=22, cert_path=cert_path)
            s = paramiko.SSHClient()
            s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            s.connect(machine, port, username, password)
            sshcopy.send()
            return
        else:
            for ip in nodes_ips:
                copy_id_to_local(hostname=ip)
                sshcopy = SshCopy(user=username, host=ip, passwd=password, port=22)
                s = paramiko.SSHClient()
                s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                s.connect(ip, port, username, password)
                sshcopy.send()
                return
    run_command(command='rm -rf .ssh/', hostname=machine, username=username, password=password)
    status = run_command(command=command, hostname=machine, username=username, password=password)
    print(status)


def machines_names():
    nodes_amt = int(get_machines_amt())
    nodes_list = []
    for node in range(nodes_amt):
        node_name = 'node' + str(node)
        if '0' in node_name:
            pass
        else:
            nodes_list.append(node_name)
    return nodes_list


def run_command(command, hostname, username, password):
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    s.connect(hostname, port, username, password)
    (stdin, stdout, stderr) = s.exec_command(command)
    channel = stdout.channel
    status = channel.recv_exit_status()
    s.close()
    return status


def copy_id_to_local(hostname, username, password):
    master_cert_path = os.getcwd() + '/master_cert'
    if not os.path.isdir(master_cert_path):
        os.mkdir(master_cert_path, 0755)
    localpath = master_cert_path + '/id_rsa.pub'
    remotepath = '/root/.ssh/id_rsa.pub'
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, username=username, password=password)
    sftp = ssh.open_sftp()
    sftp.get(remotepath=remotepath, localpath=localpath)
    sftp.close()
    ssh.close()
    return localpath


class SshCopy:
    def __init__(self, user, host, passwd, port, cert_path):
        self.pub_key = cert_path
        self.user = user
        self.host = host
        self.passwd = passwd
        self.port = port

    def send(self):
        str_ssh = '/usr/bin/ssh-copy-id -f -i %s %s@%s -p %s' % (self.pub_key, self.user, self.host, self.port)
        child = pexpect.spawn(str_ssh)
        try:
            index = child.expect(['continue connecting \(yes/no\)', '\'s password:', pexpect.EOF], timeout=20)
            print index
            if index == 0:
                child.sendline('yes')
                print child.after, child.before
            if index == 1:
                child.sendline(self.passwd)
                # child.expect('root@10.35.70.86\'s password:')
                child.expect('password:')
                child.sendline(self.passwd)
                print child.after, child.before
            if index == 2:
                print '[ failed ]'
                print child.after, child.before
                child.close()
        except pexpect.TIMEOUT:
            print child.after, child.before
            child.close()
        else:
            print 'nada feito'

if __name__ == '__main__':
    main()