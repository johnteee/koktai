#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import re


# --- 對照表定義 ---

# 臺灣閩南語羅馬字拼音對照吳守禮方音聲母表
initial_map_tl_to_bopo = {
    'p': 'ㄅ', 'ph': 'ㄆ', 'm': 'ㄇ', 'b': 'ㆠ',
    't': 'ㄉ', 'th': 'ㄊ', 'n': 'ㄋ', 'l': 'ㄌ',
    'k': 'ㄍ', 'kh': 'ㄎ', 'ng': 'ㄫ', 'g': 'ㆣ', 'h': 'ㄏ',
    'ts': 'ㄗ', 'tsh': 'ㄘ', 's': 'ㄙ', 'j': 'ㆡ',
    'tsi': 'ㄐ', 'tshi': 'ㄑ', 'si': 'ㄒ', 'ji': 'ㆢ',
    '': '',  # 代表無聲母
}

# 臺灣閩南語羅馬字拼音對照吳守禮方音韻母表
final_map_tl_to_bopo = {
    'a': 'ㄚ', 'e': 'ㆤ', 'i': 'ㄧ', 'oo': 'ㆦ', 'o': 'ㄜ', 'u': 'ㄨ',
    'ai': 'ㄞ', 'au': 'ㄠ', 'ia': 'ㄧㄚ',
    'io': 'ㄧㄜ', 'iu': 'ㄧㄨ', 'ua': 'ㄨㄚ', 'ue': 'ㄨㆤ', 'ui': 'ㄨㄧ',
    'iau': 'ㄧㄠ', 'uai': 'ㄨㄞ',
    'ann': 'ㆩ', 'enn': 'ㆥ', 'inn': 'ㆪ', 'onn': 'ㆲ',
    'm': 'ㆬ', 'ng': 'ㆭ', 'ainn': 'ㆮ', 'iann': 'ㄧㆩ', 'iaunn': 'ㄧㆯ',
    'iunn': 'ㄧㆫ', 'uann': 'ㄨㆩ', 'uannh': 'ㄨㆩㆷ', 'uainn': 'ㄨㆮ',
    'am': 'ㆰ', 'an': 'ㄢ', 'ang': 'ㄤ',
    'im': 'ㄧㆬ', 'in': 'ㄧㄣ', 'ing': 'ㄧㄥ',
    'om': 'ㆱ', 'ong': 'ㆲ', 'iam': 'ㄧㆰ',
    'ian': 'ㄧㄢ', 'iang': 'ㄧㄤ', 'iong': 'ㄧㆲ',
    'un': 'ㄨㄣ', 'uan': 'ㄨㄢ',
    'ah': 'ㄚㆷ', 'eh': 'ㆤㆷ', 'ih': 'ㄧㆷ', 'oh': 'ㄜㆷ', 'uh': 'ㄨ', 'auh': 'ㄠㆷ', 'iah': 'ㄧㄚㆷ',
    'ioh': 'ㄧㄜㆷ', 'iuh': 'ㄧㄨㆷ', 'iauh': 'ㄧㄠㆷ',
    'uah': 'ㄨㄚㆷ', 'ueh': 'ㄨㆤㆷ', 'ooh': 'ㆦㆷ',
    'annh': 'ㆩㆷ', 'ennh': 'ㆥㆷ', 'innh': 'ㆪㆷ', 'mh': 'ㆬㆷ', 'iannh': 'ㄧㆩㆷ', 'ngh': 'ㆭㆷ',
    'ap': 'ㄚㆴ', 'at': 'ㄚㆵ', 'ak': 'ㄚㆶ', 'op': 'ㆦㆴ', 'ok': 'ㆦㆶ', 'iok': 'ㄧㆦㆶ',
    'ip': 'ㄧㆴ', 'it': 'ㄧㆵ', 'ik': 'ㄧㆶ', 'iap': 'ㄧㄚㆴ', 'iat': 'ㄧㄚㆵ', 'iak': 'ㄧㄚㆶ',
    'ut': 'ㄨㆵ', 'uat': 'ㄨㄚㆵ',
    'ioo': 'ㄧㆦ', 'iooh': 'ㄧㆦㆷ',
    'ir': 'ㆨ', 'irh': 'ㆨㆷ', 'irp': 'ㆨㆴ', 'irt': 'ㆨㆵ', 'irk': 'ㆨㆶ',
    'irinn': 'ㆨㆪ', 'irm': 'ㆨㆬ', 'irn': 'ㆨㄣ', 'irng': 'ㆨㄥ',
    'er': 'ㄮ', 'ere': 'ㄮㆤ', 'erh': 'ㄮㆷ', 'ereh': 'ㄮㆤㆷ', 'erm': 'ㄮㆬ',
    'ee': 'ㄝ', 'uee': 'ㄨㄝ', 'eeh': 'ㄝㆷ', 'eng': 'ㄝㄥ',
    'or': 'ㄛ', 'orh': 'ㄛㆷ', 'ior': 'ㄧㄛ', 'iorh': 'ㄧㄛㆷ',
    'ie': 'ㄧㄝ',
    'uinn': 'ㄨㆪ', 'ionn': 'ㄧㆧ', 'uang': 'ㄨㄤ',
    'aih': 'ㄞㆷ', 'ainnh': 'ㆮㆷ', 'aunnh': 'ㆯㆷ', 'uih': 'ㄨㄧㆷ',
    'aunn': 'ㆯ', 'uenn': 'ㄨㆥ', 'uaih': 'ㄨㄞㆷ',
    'iunnh': 'ㄧㆫㆷ', 'iaunnh': 'ㄧㆯㆷ', 'uennh': 'ㄨㆥㆷ', 'uinnh': 'ㄨㆪㆷ', 'uainnh': 'ㄨㆮㆷ',
    'iut': 'ㄧㄨㆵ', 'uak': 'ㄨㄚㆶ', 'onnh': 'ㆧㆷ',
    'oi': 'ㆦㄧ', 'oih': 'ㆦㄧㆷ',
}

# 臺灣閩南語羅馬字拼音對照吳守禮方音聲調表
tone_map_tl_to_bopo = {
    '1': '', '2': 'ˋ', '3': '˪', '4': '',
    '5': 'ˊ', '6': '˫', '7': '˫', '8': '㆐', '9': '^',
    '0': '˙',  # 輕聲
    '10': '㆐' # 第8聲的另一種形式
}

教會系羅馬音標聲調符號表 = {
    'á': ('a', '2'), 'à': ('a', '3'), 'â': ('a', '5'), 'ǎ': ('a', '6'),
    'ā': ('a', '7'), 'a̍': ('a', '8'), 'a̋': ('a', '9'),
    'é': ('e', '2'), 'è': ('e', '3'), 'ê': ('e', '5'), 'ě': ('e', '6'),
    'ē': ('e', '7'), 'e̍': ('e', '8'), 'e̋': ('e', '9'),
    'í': ('i', '2'), 'ì': ('i', '3'), 'î': ('i', '5'), 'ǐ': ('i', '6'),
    'ī': ('i', '7'), 'ı̍': ('i', '8'), 'i̍': ('i', '8'), 'i̋': ('i', '9'),
    'ó': ('o', '2'), 'ò': ('o', '3'), 'ô': ('o', '5'), 'ǒ': ('o', '6'),
    'ō': ('o', '7'), 'o̍': ('o', '8'), 'ő': ('o', '9'),
    'ó͘': ('oo', '2'), 'ò͘': ('oo', '3'), 'ô͘': ('oo', '5'), 'ǒ͘': ('oo', '6'),
    'ō͘': ('oo', '7'), 'o̍͘': ('oo', '8'), 'ő͘': ('oo', '9'),
    'ú': ('u', '2'), 'ù': ('u', '3'), 'û': ('u', '5'), 'ǔ': ('u', '6'),
    'ū': ('u', '7'), 'u̍': ('u', '8'), 'ű': ('u', '9'),
    'ḿ': ('m', '2'), 'm̀': ('m', '3'), 'm̂': ('m', '5'), 'm̌': ('m', '6'),
    'm̄': ('m', '7'), 'm̍': ('m', '8'), 'm̋': ('m', '9'),
    'ń': ('n', '2'), 'ǹ': ('n', '3'), 'n̂': ('n', '5'), 'ň': ('n', '6'),
    'n̄': ('n', '7'), 'n̍': ('n', '8'), 'n̋': ('n', '9'), 'ň': ('n', '6'),
}

# --- 建立反向對照表 (方音 -> 羅馬拼音) ---

# 移除空值並反轉聲母表
bopo_to_initial_map = {v: k.replace('i', '') for k, v in initial_map_tl_to_bopo.items() if v}

# 移除空值並反轉韻母表
bopo_to_final_map = {v: k for k, v in final_map_tl_to_bopo.items() if v}

# 處理聲調對照表的重複值，建立唯一的反向對照
bopo_to_tone_map = {
    'ˋ': '2', '˪': '3', 'ˊ': '5',
    '˫': '7',  # 6、7聲同符號，依慣例使用7
    '㆐': '8',  # 8、10聲同符號，依慣例使用8
    '^': '9', '˙': '0'
}

# 將方音韻母依長度降序排序，確保優先匹配最長的韻母
# 例如：優先匹配 "ㄨㆩㆷ" (uannh) 而不是 "ㄨ" (u)
sorted_bopo_finals = sorted(bopo_to_final_map.keys(), key=len, reverse=True)

# --- 轉換邏輯 ---

def 取得白話字韻母調符對照表():
    結果 = {
        ('a', '9'): 'ă', ('e', '9'): 'ĕ', ('i', '9'): 'ĭ',
        ('o', '9'): 'ŏ', ('o͘', '9'): 'ŏ͘', ('u', '9'): 'ŭ',
        ('m', '9'): 'm̆', ('n', '9'): 'n̆',
    }
    for 白話字傳統調, 臺羅組 in 教會系羅馬音標聲調符號表.items():
        if 白話字傳統調 == 'ı̍':
            # i8有兩種unicode，踢掉跟教典不同的。
            continue

        臺羅, 數字調 = 臺羅組
        新鍵值 = 臺羅組
        if 臺羅 == 'oo':
            新鍵值 = ('o͘', 數字調)
        if 數字調 != '9':
            結果.update({新鍵值: 白話字傳統調})
    return 結果
class 臺羅轉白話字():
    白話字韻母調符對照表 = 取得白話字韻母調符對照表()

    @classmethod
    def 轉白話字(cls, 聲, 韻, 調):
        白話字聲 = cls.轉白話字聲(聲)
        白話字韻 = cls.轉白話字韻(韻)
        白話字傳統調韻 = cls.白話字韻標傳統調(白話字韻, 調)
        return (
            白話字聲 +
            白話字傳統調韻
        )

    @classmethod
    def 轉白話字聲(cls, 聲):
        白話字聲 = None
        if 聲 == 'ts':
            白話字聲 = 'ch'
        elif 聲 == 'tsh':
            白話字聲 = 'chh'
        else:
            白話字聲 = 聲
        return 白話字聲

    @classmethod
    def 轉白話字韻(cls, 韻):
        白話字韻 = None
        # 母音
        if 'oo' in 韻:
            白話字韻 = 韻.replace('oo', 'o͘')
        elif 'ua' in 韻:
            白話字韻 = 韻.replace('ua', 'oa')
        elif 'ue' in 韻:
            白話字韻 = 韻.replace('ue', 'oe')
        elif 'ing' in 韻 or 'ik' in 韻:
            白話字韻 = 韻.replace('i', 'e')
        else:
            # oo, au, ia, ai
            白話字韻 = 韻
        # 鼻化音
        if 'nnh' in 韻:
            白話字韻 = 白話字韻.replace('nnh', 'ⁿh')
        elif 'nn' in 韻:
            白話字韻 = 白話字韻.replace('nn', 'ⁿ')
        return 白話字韻

    @classmethod
    def 白話字韻標傳統調(cls, 白話字韻無調, 調):
        該標調的字 = ''
        if 'o͘' in 白話字韻無調:
            該標調的字 = 'o͘'
        elif re.search('(iau)|(oai)', 白話字韻無調):
            # 三元音 攏標佇a面頂
            該標調的字 = 'a'
        elif re.search('[aeiou]{2}', 白話字韻無調):
            # 雙元音
            if 白話字韻無調[0] == 'i':
                該標調的字 = 白話字韻無調[1]
            elif 白話字韻無調[1] == 'i':
                該標調的字 = 白話字韻無調[0]
            elif len(白話字韻無調) == 2:
                # xx
                該標調的字 = 白話字韻無調[0]
            elif 白話字韻無調[-1] == 'ⁿ' and 白話字韻無調[-2:] != 'hⁿ':
                # xxⁿ
                該標調的字 = 白話字韻無調[0]
            else:
                # xxn, xxng, xxhⁿ
                該標調的字 = 白話字韻無調[1]
        elif re.search('[aeiou]', 白話字韻無調):
            # 單元音
            該標調的字 = 白話字韻無調[0]
        elif 'ng' in 白話字韻無調:
            # ng, mng
            該標調的字 = 'n'
        elif 'm' in 白話字韻無調:
            該標調的字 = 'm'
        結果 = cls.加上白話字調符(白話字韻無調, 該標調的字, 調)
        return 結果

    @classmethod
    def 加上白話字調符(cls, 白話字韻無調, 標調字母, 調):
        if 調 == '1' or 調 == '4':
            return 白話字韻無調

        if (標調字母, 調) not in cls.白話字韻母調符對照表:
            return 白話字韻無調
        return 白話字韻無調.replace(標調字母, cls.白話字韻母調符對照表[(標調字母, 調)])

tl2poj_converter = 臺羅轉白話字()

def convert_bopo_to_tl(bopo_string):
    """
    將單一的方音字串轉換為台羅拼音。
    """
    result_tl = []
    result_poj = []
    i = 0
    while i < len(bopo_string):
        # 步驟 1: 尋找聲母
        roman_initial = ''
        # 檢查當前字符是否為聲母
        if bopo_string[i] in bopo_to_initial_map:
            roman_initial = bopo_to_initial_map[bopo_string[i]]
            i += 1

        # 步驟 2: 尋找韻母 (使用最長匹配原則)
        roman_final = ''
        found_final = False
        for final in sorted_bopo_finals:
            if bopo_string[i:].startswith(final):
                roman_final = bopo_to_final_map[final]
                i += len(final)
                found_final = True
                break
        
        if not found_final:
            # 如果找不到韻母，可能代表輸入有誤或已到字串結尾
            # 為避免無限迴圈，移動到下一個字符
            if i < len(bopo_string):
                # print(f"警告：在 '{bopo_string}' 的位置 {i} 找不到對應的韻母。")
                i += 1
            continue

        # 步驟 3: 尋找聲調符號
        tone_number = ''
        if i < len(bopo_string) and bopo_string[i] in bopo_to_tone_map:
            tone_number = bopo_to_tone_map[bopo_string[i]]
            i += 1
        else:
            # 步驟 4: 若無聲調符號，套用預設聲調規則
            # 檢查是否為入聲 (以 p, t, k, h 結尾)
            if roman_final.endswith(('p', 't', 'k', 'h')):
                tone_number = '4'
            else:
                tone_number = '1'

        result_tl.append(f"{roman_initial}{roman_final}{tone_number}")
        result_poj.append(tl2poj_converter.轉白話字(roman_initial, roman_final, tone_number))

    return "-".join(result_tl), "-".join(result_poj)



def process_entry(data):
    """
    Processes a list of dictionary entries to extract pronunciation
    from <rt> tags and create a new 'pronun_fang' field.
    
    This function recursively processes nested structures.
    """
    if isinstance(data, list):
        # If the data is a list, process each item in the list
        for item in data:
            process_entry(item)
    elif isinstance(data, dict):
        # If the data is a dictionary, look for the keys
        keys = ['entry', 'sentence']
        for key in keys:
            if key in data and isinstance(data[key], str):
                original_entry = data[key]
                
                # Find all content within <rt>...</rt> tags
                # The re.findall function returns a list of all matches
                pronunciations = re.findall(r'<rt>(.*?)</rt>', original_entry)
                # Join the found pronunciations into a single string
                if len(pronunciations) > 0:
                    data['pronun_bopo'] = "-".join(pronunciations)
                    pronun_tl, pronun_poj = convert_bopo_to_tl(data['pronun_bopo'])
                    if pronun_tl.strip() != "":
                        data['pronun_tl'] = pronun_tl
                    if pronun_poj.strip() != "":
                        data['pronun_poj'] = pronun_poj
                
                # NOTE DEPRECATED Group version but not working
                # pattern = r'((?:<rt>.*?</rt>)+)'
                # pronunciationsGroups = re.findall(pattern, original_entry)
                # # print("pronunciationsGroups", pronunciationsGroups, file=sys.stderr)
                # # Join the found pronunciations into a single string
                # if len(pronunciationsGroups) > 0:
                #     for pronunciationsGroup in pronunciationsGroups:
                #         pronunciations = re.findall(r'<rt>(.*?)</rt>', pronunciationsGroup)
                #         if len(pronunciations) > 0 and 'pronun_fang' not in data:
                #             data['pronun_fang'] = ""
                #         data['pronun_fang'] = data['pronun_fang'] + "" + "".join(pronunciations)
                
                # Remove the <rt>...</rt> tags from the original entry string
                # The re.sub function replaces the matched patterns with an empty string
                data[key] = re.sub(r'<rt>.*?</rt>', '', original_entry)

        # Recursively process any other dictionary values
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                process_entry(value)

def main():
    """
    Main function to read from stdin, process the data,
    and print the result to stdout.
    """
    try:
        # Load the entire JSON input from standard input
        # data = json.load(sys.stdin)
        # Read raw bytes from stdin to handle file encodings correctly.
        raw_data = sys.stdin.buffer.read()
        
        # Decode as UTF-8 (the standard for JSON).
        decoded_data = raw_data.decode('utf-8')
        decoded_data = re.sub(r'<img src="(.*?)"\s*>', r'\1', decoded_data)

        data = json.loads(decoded_data)
        
        # Process the loaded data
        process_entry(data)
        
        # Dump the modified JSON data to standard output
        # ensure_ascii=False is crucial for correct UTF-8 output
        # indent=2 makes the output human-readable
        print(json.dumps(data, ensure_ascii=False, indent=2))

    except json.JSONDecodeError:
        sys.stderr.write("Error: Invalid JSON format provided.\n")
    except Exception as e:
        sys.stderr.write(f"An unexpected error occurred: {e}\n")
        print(e.stacktrace, file=sys.stderr)

if __name__ == "__main__":
    main()
