import edge_tts
import os
import wave
import webrtcvad
import pyaudio
import asyncio
import time
from flask_cors import CORS

from flask import Flask, request, jsonify
from openai import OpenAI


app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "http://127.0.0.1:8080", "methods": ["GET", "POST"]}})


CHUNK = 320  # 20ms 的语音帧
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
WAVE_OUTPUT_FILENAME = "output_realtime11.wav"




def get_record():
    stream = None

    # 如果之前已经打开了音频流,先关闭它
    if stream is not None:
        stream.stop_stream()
        stream.close()

    stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                input_device_index=0)

    print("start recording")
    frames = []
    last_active_time = time.time()

    while True:
        data = stream.read(CHUNK)
        if vad.is_speech(data, RATE):
            frames.append(data)
            last_active_time = time.time()
        else:
            if time.time() - last_active_time > 1: ##可以设置声音沉默时间，这里没人说话1.5秒停止退出
                print("time:",time.time() - last_active_time )
                break


    wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    return len(frames)


def get_asr(audio_file):
    ## 启动funasr服务
    res = model.generate(input=audio_file, 
                     batch_size_s=600, hotword="小红小红"
                     )
    print(res)
    # print(res[0]["text"])
    return res

def get_llm_response(input_text):
    client = OpenAI(api_key="sk-****", base_url="https://api.deepseek.com")

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": input_text},
        ],
        stream=False
    )

    return response.choices[0].message.content
    

VOICE = "zh-CN-XiaoyiNeural"  
OUTPUT_FILE = "edgetts1.mp3"  
async def generate_tts(TEXT):
    tts = edge_tts.Communicate(text=TEXT, voice=VOICE)
    await tts.save(OUTPUT_FILE)
    # play audio 
    # playsound(OUTPUT_FILE)

# ASR Endpoint
@app.route('/start_record', methods=['GET'])
def start_record():
    
    asr_file = get_record()
    if asr_file>0:
        # try:
        voice_text = get_asr(WAVE_OUTPUT_FILENAME)  ##直接返回来text
        # print(type(voice_text))
        if "<!doctype html>" not in voice_text:
            text = voice_text[0]["text"].replace(" ","")
            print("Human:",text)
            return jsonify({'transcription': text})
        

@app.route('/ask_llm', methods=['POST'])
def ask_llm():
    
    user_input = request.json.get("text")
    llm_response = get_llm_response(user_input)
    return jsonify({'reply': llm_response})


# TTS Endpoint
@app.route('/tts', methods=['GET'])
def tts():
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    text = request.args.get('text')
    print("tts:",text)
    asyncio.run(generate_tts(text))
    return jsonify({'audio_file': OUTPUT_FILE})


if __name__ == "__main__":
    from funasr import AutoModel
    model =AutoModel(model="paraformer-zh",  vad_model="fsmn-vad",  
                            #  punc_model="ct-punc",
                  # spk_model="cam++", 
                  )
    vad = webrtcvad.Vad(3)  # 设置 VAD 的敏感度级别为 3

    p = pyaudio.PyAudio()
    app.run(host='0.0.0.0', port=2020, debug=True)

