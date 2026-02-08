// export_lif_to_sequences.ijm
requires("1.53");
run("Bio-Formats Macro Extensions");

// Args:
//   input=/path/file.lif output=/path/outroot channels=3 prefix=Ex
args = getArgument();
inPath = "";
outRoot = "";
nChannels = 3;
prefix = "Ex";

parts = split(args, " ");
for (i=0; i<parts.length; i++) {
  if (startsWith(parts[i], "input="))    inPath    = substring(parts[i], 6);
  if (startsWith(parts[i], "output="))   outRoot   = substring(parts[i], 7);
  if (startsWith(parts[i], "channels=")) nChannels = parseInt(substring(parts[i], 9));
  if (startsWith(parts[i], "prefix="))   prefix    = substring(parts[i], 7);
}
if (inPath=="" || outRoot=="") exit("ERROR: pass input=... output=... (optional: channels=3 prefix=Ex)");

File.makeDirectory(outRoot);

// Count series
Ext.setId(inPath);
Ext.getSeriesCount(seriesCount);
print("Found series: " + seriesCount);
print("Export channels: " + nChannels);

for (s=0; s<seriesCount; s++) {

  expFolder = outRoot + File.separator + prefix + (s+1);
  File.makeDirectory(expFolder);

  // Open one series windowless/quiet
  run("Bio-Formats Importer",
      "open=[" + inPath + "] autoscale color_mode=Default view=Hyperstack stack_order=XYCZT " +
      "series_" + (s+1) + " quiet windowless=true");

  if (nImages==0) exit("ERROR: Bio-Formats did not open series " + (s+1));

  origTitle = getTitle();
  selectWindow(origTitle);

  run("Split Channels");
  selectWindow(origTitle); close();

  for (c=1; c<=nChannels; c++) {
    titles = getList("image.titles");
    chTitle = "";
    for (t=0; t<titles.length; t++) {
      if (startsWith(titles[t], "C" + c + "-")) { chTitle = titles[t]; break; }
    }
    if (chTitle=="") { print("WARNING: Missing C" + c + " in " + prefix + (s+1)); continue; }

    selectWindow(chTitle);

    chFolder = expFolder + File.separator + "C" + c + "-stack_" + prefix + (s+1);
    File.makeDirectory(chFolder);

    run("Image Sequence...", "format=TIFF digits=4 start=0 save=[" + chFolder + "] name=C" + c + "-stack");
    close();
  }

  while (nImages>0) { selectImage(nImages); close(); }
  print("Done series " + (s+1));
}

print("ALL DONE.");
