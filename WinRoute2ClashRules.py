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
    result = subprocess.run(['ipconfig'], capture_output=True,
                            text=True, encoding='gbk')
    # 匹配指定网卡下的 IPv4 地址
    pattern = rf"{re.escape(adapter_keyword)}.*?IPv4.*?:\s*([\d\.]+)"
    match = re.search(pattern, result.stdout, re.S)
    if match:
        ip = match.group(1)
        print(f'虚拟网卡地址为：{ip}')
        return ip
    else:
        print(f'未找到名称包含 "{adapter_keyword}" 的虚拟网卡 IPv4 地址')
        return None


def get_routes(interface_ip):
    result = subprocess.run(['route', 'print'], capture_output=True,
                            text=True, encoding='gbk')
    lines = result.stdout.splitlines()
    routes = []
    excluded = []

    for line in lines:
        parts = line.split()
        # 路由行至少包含：目标, 掩码, 网关, 接口, 跃点数
        if len(parts) >= 5 and is_valid_ipv4(parts[0]) and is_valid_ipv4(parts[1]) and is_valid_ipv4(parts[2]):
            dest, mask, gateway, iface = parts[0], parts[1], parts[2], parts[3]
            if gateway == interface_ip:
                routes.append((dest, mask))
            else:
                excluded.append(line)

    return routes, excluded


def main():
    script_dir = os.path.dirname(os.path.realpath(__file__))
    config_file = os.path.join(script_dir, 'interface.ini')
    config = configparser.ConfigParser()

    # 读取或提示网卡名称
    if os.path.isfile(config_file):
        config.read(config_file, encoding='utf-8')
        adapter_name = config.get('INTERFACE', 'name', fallback='')
    else:
        adapter_name = ''

    interface_ip = None
    if adapter_name:
        interface_ip = get_adapter_ip(adapter_name)
        if not interface_ip:
            adapter_name = ''

    if not adapter_name:
        adapter_name = input('请输入 UU 加速器的虚拟网卡名称（如 "以太网 3"）: ')
        interface_ip = get_adapter_ip(adapter_name)
        if not interface_ip:
            print('不存在以该名称命名的网卡。')
            return
        save = input('是否保存此网卡名以便下次使用? (Y/N): ')
        if save.lower().startswith('y'):
            config['INTERFACE'] = {'name': adapter_name}
            with open(config_file, 'w', encoding='utf-8') as f:
                config.write(f)

    game_rule_name = input('请输入加速游戏的名称: ').strip()
    rules_dir = os.path.join(script_dir, 'rules')
    os.makedirs(rules_dir, exist_ok=True)

    routes, excluded = get_routes(interface_ip)

    # 写入原始 CIDR 文本
    txt_file = os.path.join(rules_dir, f'{game_rule_name}.txt')
    with open(txt_file, 'w', encoding='utf-8') as f:
        for dest, mask in routes:
            network = ipaddress.ip_network(f'{dest}/{mask}', strict=False)
            f.write(str(network) + '\n')

    # 写入 Clash 规则
    clash_file = os.path.join(rules_dir, f'{game_rule_name}.rules')
    with open(clash_file, 'w', encoding='utf-8') as f:
        f.write('payload:\n')
        for dest, mask in routes:
            network = ipaddress.ip_network(f'{dest}/{mask}', strict=False)
            f.write(f'  - {network}\n')

    # 写入 Clash No-Resolve 规则
    nores_file = os.path.join(rules_dir, f'{game_rule_name}_no-resolve.rules')
    with open(nores_file, 'w', encoding='utf-8') as f:
        f.write('payload:\n')
        for dest, mask in routes:
            network = ipaddress.ip_network(f'{dest}/{mask}', strict=False)
            f.write(f'  - {network},no-resolve\n')

    # 写入 SSTap 规则
    sstap_file = os.path.join(rules_dir, f'{game_rule_name}-SSTap.rules')
    header = f'#{game_rule_name},{game_rule_name},0,0,1,0,1,0,By-HoldOnBro'
    with open(sstap_file, 'w', encoding='utf-8') as f:
        f.write(header + '\n')
        for dest, mask in routes:
            network = ipaddress.ip_network(f'{dest}/{mask}', strict=False)
            f.write(str(network) + '\n')

    print('已生成规则文件：')
    print(txt_file, clash_file, nores_file, sstap_file)
    if excluded:
        print('\nExcluded routes:')
        for line in excluded:
            print(line)


if __name__ == '__main__':
    main()
