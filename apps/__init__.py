"""
ユーザー設定ファイルを読み込み、デフォルト設定ファイルに反映させるスクリプトファイル
列名を変更したい場合は、".\\user\\user_config.yaml" を編集してください。

"""

import os

import yaml


class NoLoader(yaml.SafeLoader):
    pass

def no_constructor(loader, node):
    return loader.construct_scalar(node)

NoLoader.add_constructor('tag:yaml.org,2002:bool', no_constructor)


dir_name = os.path.dirname(__file__)
user_config_file = os.path.join(dir_name, "user\\user_config.yaml")
default_config_file = os.path.join(dir_name, "config.yaml")


# ユーザー設定ファイルの読み込み
# もしも列名を変更したい場合は、このファイルを編集してください。
global USER_CONFIG
with open(user_config_file, 'r', encoding='utf-8') as f:
    USER_CONFIG = yaml.load(f, Loader=NoLoader)

# 実際に使用する設定ファイルの読み込み
global DEFAULT_CONFIG
with open(default_config_file, 'r', encoding='utf-8') as f:
    DEFAULT_CONFIG = yaml.load(f, Loader=NoLoader)


# drogger_gps の設定をリセット
# default_name: {'en': en_name, 'jp': jp_name}
drg_gps = DEFAULT_CONFIG['columns']['drogger_gps']
for _, items in USER_CONFIG['default'].items():
    org_name = items.get('drg-gps', None)
    if org_name is None:
        continue
    drg_gps[org_name] = {'en': items['en'], 'jp': items['jp']}
# 登録
DEFAULT_CONFIG['columns']['drogger_gps'] = drg_gps

# gyoroman_gps の設定をリセット
# default_name: {'en': en_name, 'jp': jp_name}
gyoro_gg = DEFAULT_CONFIG['columns']['gyoroman_gg_csv']
for _, items in USER_CONFIG['default'].items():
    org_name = items.get('gyoroman-gg', None)
    if org_name is None:
        continue
    gyoro_gg[org_name] = {'en': items['en'], 'jp': items['jp']}
# 登録
DEFAULT_CONFIG['columns']['gyoroman_gg_csv'] = gyoro_gg

# 元データにはないが、ユーザーが追加した列名をリセット
add_cols = DEFAULT_CONFIG['columns']['add_cols']
for key, items in USER_CONFIG['default'].items():
    if key in add_cols:
        add_cols[key] = {'en': items['en'], 'jp': items['jp']}
# 登録
DEFAULT_CONFIG['columns']['add_cols'] = add_cols

# 出力データに含めたい列名をリセット
DEFAULT_CONFIG['columns']['use_cols_en'] = USER_CONFIG['use_cols_en']



with open(default_config_file, 'w', encoding='utf-8') as f:
    yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, allow_unicode=True)

