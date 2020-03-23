import argparse
import base64
import codecs
import datetime
import json
import os
import requests
import re

parser = argparse.ArgumentParser()
parser.add_argument(
    "image_file_path",
    type=str
)
args = parser.parse_args()

os.environ["CLOUD_VISION_APIKEY"]="/home/uchida/.projectkagi/cloud_vision_apikey"

def detect_text(path):

    with open(path, 'rb') as image_file:
        content = base64.b64encode(image_file.read())
        content = content.decode('utf-8')

    with open(os.environ["CLOUD_VISION_APIKEY"], 'r') as f:
        api_key = f.readline()
    url = "https://vision.googleapis.com/v1/images:annotate?key=" + api_key
    headers = { 'Content-Type': 'application/json' }
    request_body = {
        'requests': [
            {
                'image': {
                    'content': content
                },
                'features': [
                    {
                        'type': "TEXT_DETECTION",
                        'maxResults': 10
                    }
                ],
                'imageContext': {
                    'languageHints': [
                        "ja"
                    ]
                }
            }
        ]
    }
    response = requests.post(
        url,
        json.dumps(request_body),
        headers
    )
    ocr_result = response.json()
    words = ocr_result['responses'][0]['textAnnotations'][0]['description'].strip('\n').split("\n")
    return ocr_result, words

def analyze_entity(text, language="ja"):
    with open(os.environ["CLOUD_VISION_APIKEY"], 'r') as f:
        api_key = f.readline()
    url = "https://language.googleapis.com/v1beta2/documents:analyzeEntities?key=" + api_key
    headers = { 'Content-Type': 'application/json' }
    request_body = {
        'document': {
            'content': text,
            'type': "PLAIN_TEXT",
            'language': language
        },
        'encodingType': "UTF8"
    }
    response = requests.post(
        url,
        json.dumps(request_body, ensure_ascii=False).encode('utf-8'),
        headers
    )
    result = response.json()
    # print(type(result))
    return result

# input : (path to) image
# output: record + other results

def ReceiptOCR(path_to_image):
    image_name = path_to_image.split('/')[-1]
    date_str = datetime.datetime.now().strftime("%m%d%H%M")
    all_ocr_result, detected_words = detect_text(path_to_image)
    all_nlp_result = []
    records = {"shop": [], "product": [], "price": [], "number": []}

    for each_word in detected_words: # TODO batch process
        print("analysing word: ", each_word)
        each_nlp_result = analyze_entity(each_word)
        all_nlp_result.append(each_nlp_result)
        if len(each_nlp_result['entities']) == 0:
            print("no result for ", each_word)
            continue
        entity_name = each_nlp_result['entities'][0]['name']
        entity_type = each_nlp_result['entities'][0]['type']
        if entity_type == "PRICE":
            records["price"].append(entity_name)
        elif entity_type == "ORGANIZATION":
            records["shop"].append(entity_name)
        elif entity_type == "CONSUMER_GOOD":
            records["product"].append(entity_name)
        elif entity_type == "NUMBER":
            records["number"].append(entity_name)
    
    # save all result
    with open(image_name + date_str + "all.json", "w") as f:
        content = {'all_result': all_nlp_result}
        json.dump(content, f)
    # save record
    with open(image_name + date_str +".csv", "w") as f:
        for key in records.keys():
            for each_val in records[key]:
                f.write(",".join([key, each_val]))
                f.write("\n")
    print("finished!")

if __name__ == "__main__":
    ReceiptOCR(args.image_file_path)