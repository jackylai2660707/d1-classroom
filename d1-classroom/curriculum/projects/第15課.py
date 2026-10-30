dog.stand()
if vision.wait_for("左轉卡", timeout=5):
  dog.turn_left(degrees=30)
dog.stop()
