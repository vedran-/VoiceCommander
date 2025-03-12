import os, sys
from vosk import Model, SetLogLevel

class VoskService:
    MODELS = [
        "vosk-model-small-en-us-0.15",
        "vosk-model-en-us-0.42-gigaspeech",
    ]
    #MODELS_FOLDER_PREFIX = "../vosk_models/"
    MODELS_FOLDER_PREFIX = "c:/pj/projects/VoiceCommander/vosk_models";

    def __init__(self):
        """
        self.list_models()
        model_index = int(input("\nEnter the number of the model you want to use: ")) - 1
        
        if model_index < 0 or model_index >= len(self.MODELS):
            print("Invalid model number. Exiting.")
            exit(1)

        self.load_model(model_index)
        """        
        self.load_model(0)
        

    @classmethod
    def list_models(cls):
        print("\nAvailable models:")
        for i, model_name in enumerate(cls.MODELS):
            print(f"{i + 1}. {model_name}")

    def load_model(self, model_index):
        if model_index < 0 or model_index >= len(self.MODELS):
            raise ValueError("Invalid model number.")
        
        model_path = os.path.join(self.MODELS_FOLDER_PREFIX, self.MODELS[model_index])
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model '{model_path}' not found. Please ensure the model is downloaded and in the correct directory.")

        SetLogLevel(-1000)

        self.model = Model(model_path=model_path)
    