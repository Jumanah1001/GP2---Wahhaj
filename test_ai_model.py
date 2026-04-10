from Wahhaj.AIModel import AIModel

model = AIModel(
    modelPath="weights/wahhaj_yolov8s_seg_baseline_v4_best.pt",
    confidenceThreshold=0.25,
    imageSize=640,
    device="cpu",
)
# هنا يتم تغيير باث الصورة المرغوب اختبارها 
test_image_path = r"C:\Users\robaa\Downloads\val_urban_3869.png"

detections = model.detectObjects(test_image_path)
print("Detection summary:")
print(detections["summary"])

raster = model.classifyArea(test_image_path)
print("\nRaster shape:")
print(raster.data.shape)

print("\nRaster metadata:")
print(raster.metadata)
