ObjC.import('Vision'); ObjC.import('Foundation'); ObjC.import('PDFKit'); ObjC.import('AppKit');
function recognize(cg) {
  const req = $.VNRecognizeTextRequest.alloc.init;
  req.recognitionLevel = 0;
  req.usesLanguageCorrection = true;
  req.recognitionLanguages = $(['de-DE', 'en-US', 'fr-FR', 'it-IT']);
  const handler = $.VNImageRequestHandler.alloc.initWithCGImageOptions(cg, $.NSDictionary.dictionary);
  handler.performRequestsError($([req]), null);
  const results = req.results, lines = [];
  for (let i = 0; i < results.count; i++) {
    const top = results.objectAtIndex(i).topCandidates(1);
    if (top.count) lines.push(top.objectAtIndex(0).string.js);
  }
  return lines.join('\n');
}
function cgImage(nsImage) { return nsImage.CGImageForProposedRectContextHints(null, $(), $()); }
function run(argv) {
  const path = argv[0], url = $.NSURL.fileURLWithPath(path), out = [];
  if (path.toLowerCase().endsWith('.pdf')) {
    const doc = $.PDFDocument.alloc.initWithURL(url);
    for (let i = 0; i < doc.pageCount; i++) {
      const page = doc.pageAtIndex(i), box = page.boundsForBox(0);
      const img = page.thumbnailOfSizeForBox($.NSMakeSize(box.size.width * 2, box.size.height * 2), 0);
      out.push('=== Page ' + (i + 1) + ' ===\n' + recognize(cgImage(img)));
    }
  } else {
    out.push(recognize(cgImage($.NSImage.alloc.initWithContentsOfURL(url))));
  }
  return out.join('\n');
}
