from speaker_identification import FileProcessor
import json
from pyannote.core import Segment, Timeline, Annotation
from pyannote.metrics.diarization import DiarizationErrorRate
from jiwer import wer
import os
import tqdm
from sklearn.metrics import precision_recall_fscore_support, accuracy_score
from argparse import ArgumentParser

class Evaluator:
    def __init__(self, ground_truth_dict,
                 segment_info_dict,
                 pred_trans_text: str):
        self.ground_truth_dict = ground_truth_dict
        self.ground_truth_dict = [s for s in self.ground_truth_dict if s["text"]]
        self.segment_info_dict = segment_info_dict
        self.segment_info_dict = [s for s in self.segment_info_dict if s["text"]]
        self.pred_trans_text = pred_trans_text

    def compute_diarization(self):
        reference = Annotation()
        for s in self.ground_truth_dict:
            seg = self.ground_truth_dict[s]
            reference[Segment(seg["start"],
                              seg["end"])] = seg["speaker"]
        hypothesis = Annotation()
        for s in self.segment_info_dict:
            if len(s["speaker"]):
                hypothesis[Segment(s["start"],
                                s["end"])] = s["speaker"]
        metric = DiarizationErrorRate()
        return metric(reference, hypothesis)
    
    def compute_wer(self):
        return wer(self.ground_truth_dict["text"],
                   self.pred_trans_text)
    
    def compute_speaker_classifciation_f1(self):
        try:
            assert len(self.ground_truth_dict) == len(self.segment_info_dict)
        except AssertionError:
            return -1
        g_s = [g["speaker"] for g in self.ground_truth_dict]
        p_s = [p["speaker"] for p in self.segment_info_dict]
        results = {}
        results["precision"], results["recall"], results["f1"], results["support"] = precision_recall_fscore_support(g_s, p_s, average='weighted')
        results["accuracy"] = accuracy_score(g_s, p_s)
        return results

    def evaluate(self):
        results = {}
        results["diarization"] = self.compute_diarization()
        # if "text" in self.ground_truth_dict:
        #     results["wer"] = self.compute_wer()
        results["speaker_classification_f1"] = self.compute_speaker_classifciation_f1()
        return results
        

def auto_run_speaker(file_path: str, whisper_results_file: str, denoise: bool = False, denoise_prop: float = 0.1,
                 verification_threshold: float = 0.2):
    file_processor = FileProcessor(file_path, whisper_results_file, denoise, denoise_prop, verification_threshold)
    file_processor.process(store_results=False)
    return file_processor.speaker_results

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--whisper_initial_labels", type=str, default="data/whisper_results.json")
    parser.add_argument("--ground_truth_labels", type=str, default="data/ground_truth_labels.json")
    parser.add_argument("--video_path", type=str, default="data/videos/video1.mp4")
    args = parser.parse_args()
    whisper_initial_labels = args.whisper_initial_labels
    ground_truth_labels = args.ground_truth_labels
    ground_truth_labels = json.load(open(ground_truth_labels))

    all_results = {}

    print("Denoising Proportion Variations === ")
    for denoise_prop in tqdm.tqdm([0.1, 0.2, 0.3, 0.4, 0.5]):
        speaker_results = auto_run_speaker(args.video_path, args.whisper_initial_labels, denoise=True, denoise_prop=denoise_prop, verification_threshold=0)
        evaluator = Evaluator(ground_truth_labels, speaker_results, None)
        results = evaluator.evaluate()
        all_results[denoise_prop] = results
    json.dump(all_results, open("data/all_results.json", "w"))