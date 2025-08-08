# Third-party Packages and Dependencies

Our pipeline is designed to run in a Python-based virtual environment (Python 3+) with a suite of required packages that are installed automatically upon installation. In general, we use pandas for generating, merging, and handling dataframes (pandas Development Team, 2024). Our main image processing packages are NumPy (Harris et al., 2020), Pillow (Clark, 2015), and OpenCV (Bradski, 2000). NumPy is used to convert images into arrays, which can then be used to translate specific areas of an image into full-color pixels or censored white pixels. We also use NumPy for some basic mathematical functions, such as calculating angles, distances, and areas in images. OpenCV is used in shape analysis (for the binary masks of specimen bodies) as well as for filtering out accidental partial segmentations. Pillow handles the vast majority of the image-based operations, including resizing, scaling, cropping, color conversion, mask application, drawing bounding boxes, and rotating images. We also use Matplotlib (Hunter, 2007) to plot visual maps of specimen dimensions. For all AI-based processing steps, we utilize Roboflow (​​Dwyer et al., 2024) and Anthropic (https://www.anthropic.com/api) Python packages. The last key package we use with DrawerDissect is pyYAML (https://github.com/yaml/pyyaml), which allows us to organize the pipeline with customizable inputs in a single master configuration file. 

## References

Bradski, G. (2000) The OpenCV Library. Dr. Dobb’s Journal of Software Tools, 120; 122-125.

Clark, A., 2015. Pillow (PIL Fork) Documentation, readthedocs. Available at: https://buildmedia.readthedocs.org/media/pdf/pillow/latest/pillow.pdf.

Dwyer, B., Nelson, J., Hansen, T., et al. 2024. Roboflow (Version 1.0) [Software]. Available from https://roboflow.com. Computer vision.

Harris, C. R., Millman, K. J., van der Walt, S. J., Gommers, R., Virtanen, P., Cournapeau, D., Wieser, E., Taylor, J., Berg, S., Smith, N. J., Kern, R., Picus, M., Hoyer, S., van Kerkwijk, M. H., Brett, M., Haldane, A., del Río, J. F., Wiebe, M., Peterson, P., … Oliphant, T. E. 2020. Array programming with NumPy. Nature, 585(7825): 357–362. https://doi.org/10.1038/s41586-020-2649-2

Hunter, J. D., 2007. Matplotlib: A 2D Graphics Environment, Computing in Science & Engineering, 9: 90-95.

