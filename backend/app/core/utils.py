# backend/app/core/utils.py
import re

def slugify(text: str) -> str:
    if not text:
        return ""
    # Chuyen thanh chu thuong
    text = text.lower()
    
    # Thay the ky tu tieng Viet co dau
    replacements = {
        '[àáạảãâầấậẩẫăằắặẳẵ]': 'a',
        '[èéẹẻẽêềếệểễ]': 'e',
        '[ìíịỉĩ]': 'i',
        '[òóọỏõôồốộổỗơờớợởỡ]': 'o',
        '[ùúụủũưừứựửữ]': 'u',
        '[ỳýỵỷỹ]': 'y',
        '[đ]': 'd'
    }
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text)
        
    # Xoa ky tu dac biet
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    # Thay the khoang trang va dau gach ngang lien tiep bang 1 gach ngang
    text = re.sub(r'[\s-]+', '-', text)
    # Bo gach ngang dau va cuoi chuoi
    return text.strip('-')
