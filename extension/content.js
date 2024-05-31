console.log("Content script loaded.");

function snippingTool() {
  return {
    startX: 0,
    startY: 0,
    endX: 0,
    endY: 0,
    isDrawing: false,
    overlay: null,

    startSnipping() {
      this.resetSnipping();
      this.overlay = document.createElement("div");
      this.overlay.className = "overlay";
      this.overlay.style.position = "absolute";
      this.overlay.style.border = "2px dashed #000";
      document.body.appendChild(this.overlay);
      this.attachEventListeners();
      console.log("Snipping started");
    },

    startDrawing(event) {
      this.startX = event.clientX + window.scrollX;
      this.startY = event.clientY + window.scrollY;
      this.isDrawing = true;
      this.overlay.style.left = `${this.startX}px`;
      this.overlay.style.top = `${this.startY}px`;
      this.overlay.style.width = "0px";
      this.overlay.style.height = "0px";
      console.log(`Drawing started at (${this.startX}, ${this.startY})`);
    },

    draw(event) {
      if (!this.isDrawing) return;
      this.endX = event.clientX + window.scrollX;
      this.endY = event.clientY + window.scrollY;
      this.overlay.style.width = `${Math.abs(this.endX - this.startX)}px`;
      this.overlay.style.height = `${Math.abs(this.endY - this.startY)}px`;
      this.overlay.style.left = `${Math.min(this.startX, this.endX)}px`;
      this.overlay.style.top = `${Math.min(this.startY, this.endY)}px`;
      console.log(`Cursor at (${event.clientX}, ${event.clientY})`);
      console.log(
        `Overlay position and size: left ${this.overlay.style.left}, top ${this.overlay.style.top}, width ${this.overlay.style.width}, height ${this.overlay.style.height}`,
      );
    },

    stopDrawing() {
      this.isDrawing = false;
      console.log(`Drawing stopped at (${this.endX}, ${this.endY})`);
      this.captureArea();
    },

    captureArea() {
      const x = Math.min(this.startX, this.endX);
      const y = Math.min(this.startY, this.endY);
      const width = Math.abs(this.endX - this.startX);
      const height = Math.abs(this.endY - this.startY);

      console.log(
        `Capturing area: x=${x}, y=${y}, width=${width}, height=${height}`,
      );

      browser.runtime
        .sendMessage({
          action: "captureVisibleTab",
          rect: { x, y, width, height },
        })
        .then((response) => {
          if (response.error) {
            console.error("Error capturing tab:", response.error);
            return;
          }
          const screenshotUrl = response.screenshotUrl;
          console.log("Captured Image:", screenshotUrl);

          this.downloadImage(screenshotUrl);

          fetch("http://localhost:5001/process", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              image: screenshotUrl,
              rect: { x, y, width, height },
            }),
          })
            .then((response) => response.json())
            .then((data) => {
              console.log("OCR Text:", data.text);
              console.log("Structured Data:", data.structured_data);
              console.log("Uploaded Image Path:", data.filepath);

              // Remove loading indicator
              document.body.removeChild(loading);

              // Extract the event details with defaults if undefined
              const {
                title = "TODO",
                start = "TODO",
                end = "TODO",
                description = "TODO",
                location = "TODO",
              } = data.structured_data;

              console.log(
                `Event Details: title=${title}, start=${start}, end=${end}, description=${description}, location=${location}`,
              );

              // Format the start and end dates if they are not TODO
              const startFormatted =
                start !== "TODO" ? start.replace(/[:-]/g, "") : "TODO";
              const endFormatted =
                end !== "TODO" ? end.replace(/[:-]/g, "") : "TODO";

              const calendarUrl = `https://calendar.google.com/calendar/event?action=TEMPLATE&text=${encodeURIComponent(title)}&dates=${startFormatted}/${endFormatted}&details=${encodeURIComponent(description)}&location=${encodeURIComponent(location)}`;
              console.log("Calendar URL:", calendarUrl);
              window.open(calendarUrl, "_blank");
            })
            .catch((error) => {
              console.error("Error processing image:", error);
              // Remove loading indicator
              document.body.removeChild(loading);
            });

          this.resetSnipping();
        })
        .catch((error) => {
          console.error("Error capturing tab:", error);
          this.resetSnipping();
        });
    },

    downloadImage(dataUrl) {
      const a = document.createElement("a");
      a.href = dataUrl;
      a.download = "screenshot.png";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      console.log("Image downloaded");
    },

    resetSnipping() {
      this.removeEventListeners();
      if (this.overlay) {
        document.body.removeChild(this.overlay);
      }
      this.startX = 0;
      this.startY = 0;
      this.endX = 0;
      this.endY = 0;
      this.isDrawing = false;
      this.overlay = null;
      console.log("Snipping reset");
    },

    attachEventListeners() {
      this.boundStartDrawing = this.startDrawing.bind(this);
      this.boundDraw = this.draw.bind(this);
      this.boundStopDrawing = this.stopDrawing.bind(this);
      document.addEventListener("mousedown", this.boundStartDrawing);
      document.addEventListener("mousemove", this.boundDraw);
      document.addEventListener("mouseup", this.boundStopDrawing);
    },

    removeEventListeners() {
      document.removeEventListener("mousedown", this.boundStartDrawing);
      document.removeEventListener("mousemove", this.boundDraw);
      document.removeEventListener("mouseup", this.boundStopDrawing);
    },
  };
}

window.snippingTool = snippingTool();

browser.runtime.onMessage.addListener((message) => {
  if (message.action === "startSnipping") {
    console.log("Received startSnipping message");
    const tool = snippingTool();
    tool.startSnipping();
  } else {
    console.log("Received unknown message:", message);
  }
});
