import subprocess
import re
import os
import configparser
import ipaddress


def is_reserved_ipv4(ip):
    return ipaddress.ip_address(ip).is_reserved or ipaddress.ip_address(ip).is_multicast or ipaddress.ip_address(ip).is_private


def is_valid_ipv4(ip):
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False


def get_adapter_ip(adapter_keyword):
    result = subprocess.run(['ipconfig'], capture_output=True,
                            text=True, encoding='gbk')  # 如果你的系统默认编码是utf-8，尝试更改这里
    pattern = f'{adapter_keyword}.*?IPv4.*?:\s+(.*?)\s'
    matches = re.findall(pattern, result.stdout, re.DOTALL)
    print('虚拟网卡地址为：' + matches[0])
    # findall返回的是一个列表，我们取出第一个元素（也就是第一个匹配的 ipv4 地址）
    return matches[0] if matches else None


def get_routes(interface_ip):
    result = subprocess.run(
        ['route', 'print'], capture_output=True, text=True, encoding='gbk')
    lines = result.stdout.split('\n')
    filtered_routes = []
    excluded_routes = []

    for line in lines:
        # 移除路由表开头的空格并分割
        elements = line.lstrip().split(" ")
        ip_candidate = elements[0]  # 取可能为ip的部分
        access_point = elements[3] if len(elements) > 3 else ""

        # 判断行是否不以ip形式开头，或者开头ip为保留地址，或者接口ip为保留地址
        if not is_valid_ipv4(ip_candidate) or is_reserved_ipv4(ip_candidate) or (access_point and access_point != interface_ip):
            excluded_routes.append(line)
        elif interface_ip in line:
            filtered_routes.append(line)

    return filtered_routes, excluded_routes

script_dir = os.path.dirname(os.path.realpath(__file__))
config_file = os.path.join(script_dir, 'interface.ini')
config = configparser.ConfigParser()

adapter_name = ''

if os.path.isfile(config_file):
    config.read(config_file)
    adapter_name = config.get('INTERFACE', 'name', fallback='')
    interface_ip = get_adapter_ip(adapter_name)
    if not interface_ip:
        adapter_name = ''

if not adapter_name:
    adapter_name = input('请输入UU加速器的虚拟网卡名称，如“以太网 3”（网卡名称可在cmd内执行ipconfig查看）： ')
    interface_ip = get_adapter_ip(adapter_name)
    if interface_ip:
        save_config = input('需要保存该网卡名以供下次直接使用吗？（将写入到interface.ini文件） (Y/N): ')
        if save_config.lower() in ['yes', 'y', 'Y']:
            config['INTERFACE'] = {'name': adapter_name}
            with open(config_file, 'w') as f:
                config.write(f)
    else:
        print('不存在以该名称命名的网卡。')
        exit(1)

game_rule_name = input("请输入加速游戏的名称，如“APEX”：")
rules_dir = os.path.join(script_dir, 'rules')
if not os.path.exists(rules_dir):
    os.makedirs(rules_dir)
output_file_txt = os.path.join(rules_dir, f'{game_rule_name}.txt')
output_file_rules = os.path.join(rules_dir, f'{game_rule_name}.rules')
output_file_sstap_rules = os.path.join(
    rules_dir, f'{game_rule_name}-SSTap.rules')

matching_routes, excluded_routes = get_routes(interface_ip)

with open(output_file_txt, 'w') as f:
    for route in matching_routes:
        elements = route.split()  # 使用空格分割
        ip_cidr = ipaddress.ip_network(elements[0] + "/" + elements[1])
        f.write(str(ip_cidr) + '\n')

with open(output_file_rules, 'w') as f:
    f.write('payload:\n')
    for route in matching_routes:
        elements = route.split()  # 使用空格分割
        ip_cidr = ipaddress.ip_network(elements[0] + "/" + elements[1])
        f.write('  - ' + str(ip_cidr) + '\n')

with open(output_file_sstap_rules, 'w') as f:
    f.write('#' + game_rule_name + ',' + game_rule_name +
            ',0,0,1,0,1,0,By-HoldOnBro\n')
    for route in matching_routes:
        elements = route.split()  # 使用空格分割
        ip_cidr = ipaddress.ip_network(elements[0] + "/" + elements[1])
        f.write(str(ip_cidr) + '\n')

print('Excluded routes:')
for route in excluded_routes:
    print(route)
