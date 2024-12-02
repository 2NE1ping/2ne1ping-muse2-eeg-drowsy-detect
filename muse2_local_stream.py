import time
import requests
import numpy as np
from pylsl import StreamInlet, resolve_stream
from datetime import datetime
from scipy.signal import stft

# Flask 서버 URL
SERVER_URL = "http://hci-kibana.duckdns.org/muse2"

# STFT 설정
fs = 256  # 샘플링 속도 (Hz)
nperseg = 256  # 창 크기
noverlap = 128  # 겹침

# 주파수 대역 분석 함수
def calculate_brainwave_bands(frequencies, amplitudes):
    """주파수 대역별 분석"""
    bands = {
        "Theta": (4, 8),
        "Alpha": (8, 13),
        "Beta": (13, 30),
    }
    results = {}
    for band, (low, high) in bands.items():
        mask = (frequencies >= low) & (frequencies < high)
        results[band] = amplitudes[mask].mean()  # 특정 대역의 평균 진폭 계산
    return results

# Flask로 데이터 전송
def send_to_flask(data):
    """Flask 서버로 데이터 전송"""
    try:
        response = requests.post(SERVER_URL, json=data)
        if response.status_code == 200:
            print(f"Sent to Flask: {data}")
        else:
            print(f"Failed to send to Flask: {response.status_code}, {response.text}")
    except Exception as e:
        print(f"Error sending to Flask: {e}")

# EEG 데이터 스트림 처리
print("Looking for an EEG stream...")
streams = resolve_stream('type', 'EEG')

# 데이터 스트림 연결
inlet = StreamInlet(streams[0])
print("Muse2 Streaming started")

try:
    # 데이터 버퍼
    af7_buffer = []
    af8_buffer = []
    buffer_size = nperseg  # STFT 창 크기

    while True:
        sample, timestamp = inlet.pull_sample()
        readable_timestamp = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')

        # AF7, AF8 데이터를 각각 버퍼에 추가
        af7_buffer.append(sample[1])  # AF7 채널 데이터
        af8_buffer.append(sample[2])  # AF8 채널 데이터

        # 버퍼가 충분히 쌓이면 STFT 수행
        if len(af7_buffer) >= buffer_size and len(af8_buffer) >= buffer_size:
            # 버퍼 데이터를 NumPy 배열로 변환
            af7_array = np.array(af7_buffer[-buffer_size:])  # 최신 데이터만 유지
            af8_array = np.array(af8_buffer[-buffer_size:])  # 최신 데이터만 유지

            # STFT 수행
            f_af7, _, Zxx_af7 = stft(af7_array, fs=fs, nperseg=nperseg, noverlap=noverlap)
            f_af8, _, Zxx_af8 = stft(af8_array, fs=fs, nperseg=nperseg, noverlap=noverlap)

            amplitudes_af7 = np.abs(Zxx_af7)
            amplitudes_af8 = np.abs(Zxx_af8)

            # 주파수 대역 분석
            brainwave_bands_af7 = calculate_brainwave_bands(f_af7, amplitudes_af7[:, -1])  # AF7 최신 시간 창
            brainwave_bands_af8 = calculate_brainwave_bands(f_af8, amplitudes_af8[:, -1])  # AF8 최신 시간 창

            # 평균 값 계산
            averaged_bands = {
                "Theta": (brainwave_bands_af7["Theta"] + brainwave_bands_af8["Theta"]) / 2,
                "Alpha": (brainwave_bands_af7["Alpha"] + brainwave_bands_af8["Alpha"]) / 2,
                "Beta": (brainwave_bands_af7["Beta"] + brainwave_bands_af8["Beta"]) / 2,
            }

            # 결과 데이터 구성
            eeg_data_processed = {
                "timestamp": readable_timestamp,
                "Theta": averaged_bands["Theta"],
                "Alpha": averaged_bands["Alpha"],
                "Beta": averaged_bands["Beta"],
            }

            # Flask로 전송
            send_to_flask(eeg_data_processed)

        # 0.1초 대기
        time.sleep(1)

except KeyboardInterrupt:
    print("Streaming stopped by user.")
