from speechbrain.pretrained import SepformerSeparation as separator
import torchaudio
import glob
import numpy as np
import torch
import torchaudio
import os
from scipy.io import wavfile
import pprint
from asteroid.metrics import get_metrics


model = separator.from_hparams(source="speechbrain/sepformer-whamr-enhancement", savedir='pretrained_models/sepformer-whamr-enhancement', run_opts={'device':'cuda'})

window_sizes = [1000]
SAMPLING_RATE = 8000

mix_paths = sorted(glob.glob("/content/SIU-test-dataset/mix/*.wav"))

save_pth = "/content/sepformer8k/mix_1000"
def evaluate_model(input_pth):

    audio_data = [torchaudio.load(aud_pth, normalize=True)[0] for aud_pth in mix_paths] #Take the folder path and open all the audio files here

    for window_size in window_sizes:
        audio_index = 0
        for audio in audio_data:
            audio = torchaudio.transforms.Resample(16000, SAMPLING_RATE)(audio)
            audio_len = audio.shape[1]
            res = torch.Tensor(1, 1).to('cuda')

            prev_ind = 0
            for a in range(min(int(window_size/1000*SAMPLING_RATE), audio_len-1), audio_len, int(window_size/1000*SAMPLING_RATE)):
                audio_ptorch = audio[0][prev_ind:a].unsqueeze(0)
                output = model.separate_batch(audio_ptorch).squeeze(2)
                
                res = torch.cat( (res, output), dim=1)

                prev_ind = a
            
            res_path = os.path.join(save_pth, os.path.split(mix_paths[audio_index])[-1].split(".")[0] +  ".wav")
            wavfile.write(res_path, SAMPLING_RATE, res[0].cpu().numpy().astype(np.float32))
            audio_index += 1

    res_dict = {
      'input_pesq': 0.0,
      'input_sar': 0.0,
      'input_sdr': 0.0,
      'input_si_sdr': 0.0,
      'input_sir': 0.0,
      'input_stoi': 0.0,
      'pesq': 0.0,
      'sar': 0.0,
      'sdr': 0.0,
      'si_sdr': 0.0,
      'sir': 0.0,
      'stoi': 0.0
      }
    
    #mix_paths = glob.glob("/content/SIU-test-dataset/mix/*.wav")
    clean_paths = glob.glob("/content/SIU-test-dataset/clean/*.wav")
    res_paths = glob.glob("/content/sepformer8k/mix_1000/*.wav")

    for mix_path, clean_path, res_path in zip(sorted(mix_paths), sorted(clean_paths), sorted(res_paths)):
      #compute metrics here
      mix = open_audio(mix_path)
      clean = open_audio(clean_path)
      est = open_audio(res_path)

      min_len = min(mix.shape[0], clean.shape[0], est.shape[0])
      mix = np.expand_dims(mix[0: min_len], axis=0) / 32768.0
      mix = np.clip(np.where(np.isnan(mix), 0, mix), 0, 1)

      clean = np.expand_dims(clean[0: min_len], axis=0) / 32768.0
      clean = np.clip(np.where(np.isnan(clean), 0, clean), 0, 1)

      est = np.expand_dims(est[0: min_len], axis=0)
      est = np.clip(np.where(np.isnan(est), 0, est), 0, 1)

      metrics_dict = get_metrics(mix, clean, est, sample_rate=SAMPLING_RATE, metrics_list='all')

      for key in res_dict:
        res_dict[key] += metrics_dict[key]


    pprint.pprint(res_dict)


