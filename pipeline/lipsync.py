import requests
import os
import time
import base64
from dotenv import load_dotenv

load_dotenv()

RAW_KEY = os.getenv("DID_API_KEY")
DID_API_KEY = base64.b64encode(RAW_KEY.encode()).decode()
DID_API_URL = "https://api.d-id.com"

def get_headers():
    return {
        "Authorization": f"Basic {DID_API_KEY}",
        "Accept": "application/json"
    }

def upload_video_to_did(video_path):
    with open(video_path, "rb") as f:
        response = requests.post(
            f"{DID_API_URL}/videos/uploads",
            headers=get_headers(),
            files={"video": (os.path.basename(video_path), f, "video/mp4")}
        )
    print("Video upload:", response.status_code)
    response.raise_for_status()
    return response.json()["url"]

def upload_audio_to_did(audio_path):
    with open(audio_path, "rb") as f:
        response = requests.post(
            f"{DID_API_URL}/audios/uploads",
            headers=get_headers(),
            files={"audio": (os.path.basename(audio_path), f, "audio/wav")}
        )
    print("Audio upload:", response.status_code)
    response.raise_for_status()
    return response.json()["url"]

def create_lipsync_job(video_url, audio_url):
    headers = get_headers()
    headers["Content-Type"] = "application/json"
    response = requests.post(
        f"{DID_API_URL}/clips",
        headers=headers,
        json={
            "video_url": video_url,
            "audio_url": audio_url
        }
    )
    print("Clip creation:", response.status_code, response.text)
    response.raise_for_status()
    return response.json()["id"]

def wait_for_job(job_id, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        response = requests.get(
            f"{DID_API_URL}/clips/{job_id}",
            headers=get_headers()
        )
        data = response.json()
        status = data.get("status")
        print(f"D-ID status: {status}")
        if status == "done":
            return data.get("result_url")
        elif status == "error":
            raise Exception(f"D-ID error: {data.get('error')}")
        time.sleep(5)
    raise Exception("D-ID job timed out")

def download_video(url, output_path):
    response = requests.get(url, stream=True)
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    return output_path

def lipsync_video(video_path, audio_path, output_path="output/lipsync_final.mp4"):
    print("Uploading video to D-ID...")
    video_url = upload_video_to_did(video_path)

    print("Uploading audio to D-ID...")
    audio_url = upload_audio_to_did(audio_path)

    print("Creating lip sync job...")
    job_id = create_lipsync_job(video_url, audio_url)

    print(f"Waiting for D-ID (job: {job_id})...")
    result_url = wait_for_job(job_id)

    print("Downloading lip synced video...")
    download_video(result_url, output_path)

    print(f"Lip sync complete: {output_path}")
    return output_path
