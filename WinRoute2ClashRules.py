import subprocess
import re
import os
import configparser
import ipaddress

def is_valid_ipv4(ip):
    try:
        ipaddress.IPv4Address(ip)
        return True
    except ipaddress.AddressValueError:
        return False

def get_adapter_ip(adapter_keyword):
    result = subprocess.run(['ipconfig'], capture_output=True, text=True, encoding='gbk')  # 如果你的系统默认编码是utf-8，尝试更改这里
    pattern = f'{adapter_keyword}.*?IPv4.*?:\s+(.*?)\s'
    matches = re.findall(pattern, result.stdout, re.DOTALL)
    print(matches)
    return matches[0][1] if matches else None  # findall返回的是一个列表，我们取出第一个元素（也就是第一个匹配）的第二个组

def get_routes(adapter_name):
    result = subprocess.run(['route', 'print'], capture_output=True, text=True, encoding='gbk')
    lines = result.stdout.split('\n')
    filtered_routes = []
    excluded_routes = []

    for line in lines:
        stripped_line = line.lstrip()  # 移除路由表开头的空格
        ip_candidate = stripped_line.split(" ")[0]  # 取可能为ip的部分

        # 判断行是否存在“在链路上”，或者不以ip形式开头
        if  "在链路上" in stripped_line or not is_valid_ipv4(ip_candidate):
            excluded_routes.append(stripped_line)
        elif adapter_name in line:
            filtered_routes.append(stripped_line)
    
    return filtered_routes, excluded_routes

def convert_to_cidr(ip, netmask):
    # 将网络掩码转换为CIDR形式
    binary_str = ''
    for octet in netmask.split('.'):
        binary_str += bin(int(octet))[2:].zfill(8)
    netmask = str(len([bit for bit in binary_str if bit == '1']))
    return ip + '/' + netmask

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
output_file_txt = os.path.join(script_dir, f'{game_rule_name}.txt')
output_file_rules = os.path.join(script_dir, f'{game_rule_name}.rules')

matching_routes, excluded_routes = get_routes(interface_ip)

with open(output_file_txt, 'w') as f:
    for route in matching_routes:
        elements = route.split()  # 使用空格分割
        ip_cidr = convert_to_cidr(elements[0], elements[1])
        f.write(ip_cidr + '\n')

with open(output_file_rules, 'w') as f:
    f.write('payload:\n')
    for route in matching_routes:
        elements = route.split()  # 使用空格分割
        ip_cidr = convert_to_cidr(elements[0], elements[1])
        f.write('  - ' + ip_cidr + '\n')

#print('Excluded routes:')
#for route in excluded_routes:
#    print(route)
