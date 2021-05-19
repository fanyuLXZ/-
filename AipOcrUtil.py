from aip import AipOcr

# 初始化
aip_ocr = AipOcr("19940233", "2pp3gIWzK8RxCuTfgPCtqKGr", "EbFTQyU6K2tqhV8xfbSdCZAogHGNwSZN")


# 获取文字str
def get_str(image):
    image_date = aip_ocr.basicGeneral(image)
    return image_date['words_result'][0]['words']
