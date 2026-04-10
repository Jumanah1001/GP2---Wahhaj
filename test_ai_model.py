from Wahhaj.AIModel import AIModel

model = AIModel(
    modelPath="weights/wahhaj_yolov8s_seg_baseline_v4_best.pt",
    confidenceThreshold=0.25,
    imageSize=640,
    device="cpu",
)

result = model.detectObjects("path/to/test_image.jpg")
print(result["summary"])

raster = model.classifyArea("path/to/test_image.jpg")
print(raster.data.shape)
print(raster.metadata)
