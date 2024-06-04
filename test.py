
def intToRoman(num: int) -> str:
    sym_map = {
        1: 'I',
        5: 'V',
        10: 'X',
        50: 'L',
        100: 'C',
        500: 'D',
        1000: 'M'
    }
    first_num = str(num)[0]
    letters = ''
    if first_num in ['4','9']:
        highest_sub = 0
        for idx, v in enumerate(sym_map):
            if num - v < 0:
                letters += sym_map[idx-1] + sym_map[idx]
                highest_sub = v
                break
        rem = abs(highest_sub-num)
        print(rem)
        if rem != 0:
            new_letters = intToRoman(rem)
            letters += new_letters
    else:
        highest_sub = 0
        for idx, v in enumerate(sym_map):
            if num - v < 0:
                letters += sym_map[idx-1]
                highest_sub = v
                break
        rem = abs(highest_sub-num)
        print(rem)
        if rem != 0:
            new_letters = intToRoman(rem)
            letters += new_letters
    print(letters)
    return letters


intToRoman(3749)