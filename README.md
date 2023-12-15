# MSReact

MSReact is a novel software framework that can facilitate the creation of intelligent mass spectrometry acquisition methods. This repository hosts the initial version of MSReact Python client.

## Important note
Vendor licensing model requires specific and restrictive signed agreements, limiting the possibility to openly distribute the MSReact server component. The latter is foreseen to be released in a closed-source form and under a specific distribution agreement soon.

## Prerequisites
* Install Python >3.9.7
* Install necessary Python modules from `client/pymsreact/pymsreact/requirements.txt`

## Usage

The MSReact Python Client provides a framework to create novel intelligent mass spectrometry acquisition methods. To use the framework clone the `MSReact` repository.

**Creating new workflows**

* Make a copy of `client/pymsreact/pymsreact/algorithms/prototypes/template.py` and leave it in the prototypes directory.
	
* Define activities in the functions of the `Acquisition` class:
	```
	class YourAcquisition(Acquisition):
    
    def __init__(self, *args):
        super().__init__(*args)
        self.name = 'template_acquisition'
        
    def pre_acquisition(self):
	    # Load data from file before acquisition
		...
	def intra_acquisition(self):
		# While the acquisition is running, request MS1 scans, analyse received
		# MS1 scans and request MS2 scans based on the decision.
		...
	def post_acquisition(self):
		# Save data to file after acquisition
		...
	```
* Add created acquisitions to the `acquisition_sequence` of the `Algorithm` class, that serves as a container for different acquisitions:
	```
	class YourAlgorithm(Algorithm):
	
		def __init__(self):
        super().__init__()
        self.acquisition_sequence = [ YourAcquisition1, YourAcquisition2 ]
	```

	For further inspiration, check out the top_n_test_algo module.

**Running the created workflows**
* The created algorithms are discovered by the Python client. 
* Run the client from `client/pymsreact`
* For further help in the use of pymsreact select the help command:
	```
	python pymsreact --help
	```

## Remarks

This project has received funding from the European Union’s Horizon 2020 research and innovation programme under the Marie Skłodowska-Curie grant agreement Nº 956148 ![eu_flag](https://github.com/proteotoul/MSReact/blob/main/images/eu_flag.jpg?raw=true)