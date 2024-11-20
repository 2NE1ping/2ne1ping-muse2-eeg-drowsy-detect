from pylsl import StreamInlet, resolve_stream
from datetime import datetime
import json
import requests
import csv

# ElasticSearch endpoint와 인증 정보
ELASTICSEARCH_URL = "http://hci-kibana.duckdns.org:9200/eeg-stream-data/_doc"
HEADERS = {"Content-Type": "application/json"}
USERNAME = "hci"  # Azure ElasticSearch 사용자 이름
PASSWORD = "hcihci"  # Azure ElasticSearch 비밀번호

# CSV 파일 초기화
csv_file_path = "eeg_data_stream_all.csv"
with open(csv_file_path, mode="w", newline="") as file:
    writer = csv.writer(file)
    # CSV 파일의 헤더 작성
    writer.writerow(["timestamp", "TP9", "AF7", "AF8", "TP10", "Right AUX"])

# EEG 데이터 스트림을 찾습니다.
print("Looking for an EEG stream...")
streams = resolve_stream('type', 'EEG')

# 데이터 스트림 연결
inlet = StreamInlet(streams[0])

print("Streaming data to ElasticSearch and saving to CSV... Press Ctrl+C to stop.")
try:
    while True:
        # 데이터를 가져옵니다.
        sample, timestamp = inlet.pull_sample()

        # 타임스탬프를 읽기 쉬운 형식으로 변환
        readable_timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')

        # 필요한 데이터 JSON 구조로 변환
        eeg_data = {
            "timestamp": readable_timestamp,
            "TP9": sample[0],
            "AF7": sample[1],
            "AF8": sample[2],
            "TP10": sample[3],
            "Right AUX": sample[4]
        }

        # ElasticSearch로 데이터 전송
        response = requests.post(
            ELASTICSEARCH_URL,
            headers=HEADERS,
            data=json.dumps(eeg_data),
            auth=(USERNAME, PASSWORD)
        )

        if response.status_code == 201:
            print(f"Data indexed successfully: {eeg_data}")

            # CSV 파일에 데이터 추가
            with open(csv_file_path, mode="a", newline="") as file:
                writer = csv.writer(file)
                writer.writerow([
                    eeg_data["timestamp"],
                    eeg_data["TP9"],
                    eeg_data["AF7"],
                    eeg_data["AF8"],
                    eeg_data["TP10"],
                    eeg_data["Right AUX"]
                ])
        else:
            print(f"Failed to index data: {response.text}")

except KeyboardInterrupt:
    print("\nStreaming stopped.")

