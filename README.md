# Fragment Intensity Prediction

### CNN(B) Architecture 


![my_model](https://user-images.githubusercontent.com/124587762/217084872-7f2341ed-9818-4233-afd5-27c24fd39bbf.jpg)

This model takes two inputs: a 7-dimensional vector representing precursor charge (Input A) and a 30x22 matrix representing peptide sequence(Input B), both of which were one-hot encoded. The peptide sequence input is processed through two 1D convolutional layers in combination with max pooling layers. The output of the convolutional layers is then flattened. The precursor charge input is passed through a max pooling layer and, after that, through a dense layer with ReLU activation and is concatenated with the output produced by peptide sequence input. The concatenated layers are then passed through another dense layer with ReLU activation before finally being passed through a dense layer with 56 units and sigmoid activation to produce the output (Figure above). The model was compiled using the Model class from the Keras library. It was trained with spectral angle as a loss function, the Adam optimizer from Keras library, and a batch size of 128 over 10 epochs. The output of this model is 56-dimensional tensor, with first 28 elements representing the normalized intensities of b ions and the last 28 elements representing the normalized intensities of the y ions.
