from image_processor import GeminiImageProcessor


processor = GeminiImageProcessor()


image_path = "test_image.png"


result = processor.analyze_image(
    image_path=image_path
)


print("\n")
print("=" * 70)
print("IMAGE ANALYSIS")
print("=" * 70)
print(result)