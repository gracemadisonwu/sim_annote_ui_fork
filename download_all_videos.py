import gdown
import os

if __name__ == "__main__":
    # UAB video
    # 1uT_DgTdgw39GNMGOw40v4FAZ-FGyNzqv
    for folder_name, file_id, whisper_file in [
        ("uab_video", "1uT_DgTdgw39GNMGOw40v4FAZ-FGyNzqv", "1ss4KheR_dHBTyUAQHqHJIL_Pgwva6bC9"),
        ("trauma_a_video", "1k8JXDYtLroyAHOJkR3ajjD2D2rk_KRUR", "1uDv8nOfqzJIp13m2fvpOvuS20OjGVpha"),
        ("original", "1UBq-gPxE8R5VBv9bdlv7KcRZnVmm02Z9", "1u4dAHxjYH1XD0GuS2kDJ76G6XTTKPJXk"),
        ("neo_cam_video", "1WEeTiGDh6Q-C5fw8lq6GNEL9Ex6Z68pU", "1QRmrGPuOTXv4KdW0wGJVw0a2MX2G-DwC")
    ]:
        os.makedirs(f"uploads/{folder_name}/", exist_ok=True)
        url = f'https://drive.google.com/uc?id={file_id}'
        output_fname = gdown.download(url, f"uploads/{folder_name}/video.mp4", quiet=False)
        url = f'https://drive.google.com/uc?id={whisper_file}'
        output_fname = gdown.download(url, f"uploads/{folder_name}/whisper_results.json", quiet=False)