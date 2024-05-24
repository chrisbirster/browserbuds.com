console.log("Background script loaded.");

browser.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "captureVisibleTab") {
    const { rect } = message;

    browser.tabs
      .captureVisibleTab(null, {
        format: "png",
        rect: {
          x: rect.x,
          y: rect.y,
          width: rect.width,
          height: rect.height,
        },
      })
      .then((screenshotUrl) => {
        sendResponse({ screenshotUrl });
      })
      .catch((error) => {
        sendResponse({ error: error.message });
      });

    return true; // Indicates you wish to send a response asynchronously
  }
});
