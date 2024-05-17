# Set up a Conda Environment for COLORoptera

Make sure that conda is installed and updated. Then, create a new conda environment that includes all the necessary packages.

<div>
    <button onclick="copyToClipboard('#codeBlock')">Copy</button>
</div>

<pre id="codeBlock">
conda create -n &lt;your-env-name&gt; -c conda-forge python=3.9 pillow pandas pytesseract tesseract pip
</pre>

<script>
function copyToClipboard(element) {
    var temp = document.createElement('textarea');
    temp.value = document.querySelector(element).innerText;
    document.body.appendChild(temp);
    temp.select();
    document.execCommand('copy');
    document.body.removeChild(temp);
    alert('Copied to clipboard');
}
</script>

Then, pip install roboflow. Roboflow can sometimes install weirdly, so it's good to specify exactly where you want it to go.

```/home/<your-username>/miniconda3/envs/<your-env-name>/bin/python -m pip install roboflow```

