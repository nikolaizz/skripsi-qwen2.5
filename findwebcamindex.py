import cv2

# Fungsi untuk mencari webcam yang tersedia
def find_webcams():
    available_webcams = []
    
    # Coba indeks dari 0 sampai 9 (biasanya webcam pertama memiliki indeks 0, dan seterusnya)
    for index in range(10):
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            available_webcams.append(index)
            cap.release()
    
    return available_webcams

# Menampilkan hasil
webcams = find_webcams()
if webcams:
    print("Webcam yang tersedia ditemukan pada indeks berikut:")
    print(webcams)
else:
    print("Tidak ada webcam yang ditemukan.")

