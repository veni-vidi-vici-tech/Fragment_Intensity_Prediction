import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.model_selection import GroupShuffleSplit
from sklearn.model_selection import GroupKFold
from sklearn.utils import shuffle
from scipy import spatial
import scipy.stats as stats

def clean_data(df):
  '''
  Checks the DataFrame for errors and noise and
  returns it without them
  '''
  # 2.1 Removing join errors
  df['precursor_max'] = df.groupby(['peptide_sequence', 'scan_number', 'raw_file'])['precursor_charge'].transform(max)
  df['precursor_min'] = df.groupby(['peptide_sequence', 'scan_number', 'raw_file'])['precursor_charge'].transform(min)
  df.loc[df['precursor_max'] != df['precursor_min']]
  df.drop(df.index[df['precursor_max'] != df['precursor_min']], inplace = True)
  df.drop(['precursor_max', 'precursor_min'], axis=1, inplace=True)

  # 2.2 Removing noise from the data
  df.drop(df.index[df["peptide_sequence"].str.len() == df['no']], inplace = True)
  return df

def normalize_intensity(df):
  '''
  Takes intensity values from the DataFrame, normalizes them using
  cumulative intensity normalization method and returns the DataFrame
  with the new normalized values in a ['normalized_intensity'] column
  '''
  # 1. Assigning rank to every intensity in the spectra
  df['rank'] = df.groupby(['peptide_sequence', 'scan_number', 'raw_file'])["intensity"].rank("dense", ascending=False)

  # 2. Calculating intensity total within each spectra
  df['total'] = df.groupby(['peptide_sequence', 'scan_number', 'raw_file'])["intensity"].transform('sum')

  # 3. Sorting values within the spectra based on their rank
  df['sum_greater_than'] = df.sort_values('rank', ascending=False).groupby(['peptide_sequence', 'scan_number', 'raw_file'])['intensity'].cumsum()

  # 4. Calculating the normalized intensity values within the spectra
  df['normalized_intensity'] = df['sum_greater_than']/df['total']

  # 5. Dropping helper-columns
  df.drop(['rank', 'sum_greater_than', 'total'], axis = 1, inplace = True)
  df
  return df

def create_target():
  df['group'] = df.groupby(['peptide_sequence', 'scan_number', 'raw_file']).ngroup()
  # df['group'] = df.groupby(['peptide_sequence', 'precursor_charge']).ngroup()
  groups = df.groupby('group')
  result = []
  for name, group in groups:
    intensities = np.zeros(56)
    ion_groups = group.groupby('ion_type')

    for ion_name, ion_group in ion_groups:
      if ion_name == 'b':
        indices = ion_group['no'] - 1
        #intensities[indices] = ion_group['mean_normalized_intensity'].values
        intensities[indices] = ion_group['normalized_intensity'].values
      else:
        indices = 27 + ion_group['no']
        #intensities[indices] = ion_group['mean_normalized_intensity'].values
        intensities[indices] = ion_group['normalized_intensity'].values
    result.append(intensities)

def encode_peptides(df):

  # 1. Make sure that all the sequences have the same length
  # Finding the longest sequence
  max_len = df['peptide_sequence'].str.len().max()
  # Addding dummy values to shorter sequences to achieve the same length for every sequence
  df['peptide_sequence_encoded'] = df['peptide_sequence'].apply(lambda x: x + 'X'*(max_len - len(x)))
  # 2. Separate all the letters with comma
  df['peptide_sequence_encoded'] = df['peptide_sequence_encoded'].agg(lambda x: ','.join(x))
  # 3. Replace one-letter code with numbers
  # Creating a dictionary, where dummy value X, every amino acid and 'O'(oxidized methionine) is numbered
  aa_dict = {'X' : '0',
             'A' : '1', 'C' : '2', 'D' : '3',
             'E' : '4', 'F' : '5', 'G' : '6',
             'H' : '7', 'I' : '8', 'K' : '9',
             'L' : '10', 'M' : '11', 'N' : '12',
             'P' : '13', 'Q' : '14', 'R' : '15',
             'S' : '16', 'T' : '17', 'V' : '18',
             'W' : '19', 'Y' : '20', 'O' : '21'}
  # Iterating over all key-value pairs in aa_dict dictionary
  for key, value in aa_dict.items():
      # Replace key character(one letter code) with value character(number) in a sequence
      df['peptide_sequence_encoded'] = df['peptide_sequence_encoded'].apply(lambda x: x.replace(key, value))

  # 4. Turn string of numbers into integers
  df['peptide_sequence_encoded'] = df['peptide_sequence_encoded'].apply(lambda x: [int(i) for i in x.split(",")])


def split_train_test(df, test_size):
  '''
  Splits the df into train and test splits
  '''

  # Create a new column in your dataframe that groups rows with the same peptide sequence value
  df['peptide_group'] = df.groupby('peptide_sequence').ngroup()

  # Create an instance of GroupShuffleSplit
  gss = GroupShuffleSplit(n_splits=1, test_size=test_size)

  # Split your dataframe into train and test sets using the iterator
  for train_index, test_index in gss.split(df, groups=df['peptide_group']):
      training = df.iloc[train_index]
      test_df = df.iloc[test_index]

  return training, test_df

def find_common_peptides(df_1, df_2):
  '''
  Finds common peptides between df_1 and df_2
  '''
  df_1_peptides = set(df_1['peptide_sequence'])
  df_2_peptides = set(df_2['peptide_sequence'])

  common_peptides = df_1_peptides & df_2_peptides
  print(common_peptides)

def calculate_precursor_percentage(splitted_df, original_df):
  '''
  Calculates the percentage of precursor charge values in the train split
  '''
  precursor_charge_counts = splitted_df['precursor_charge'].value_counts()
  return ((precursor_charge_counts / original_df['precursor_charge'].value_counts()) * 100)


def calculate_peptide_length_percentage(splitted_df, original_df):
  '''
  Calculates the percentage of precursor charge values in the train split
  '''
  peptide_length_counts = splitted_df['peptide_length'].value_counts()
  return ((peptide_length_counts / original_df['peptide_length'].value_counts()) * 100)

def save_test(test_df):
  '''
  Transforms test_df into right format
  and saves it as 3 NumPy arrays
  '''
  # Transforming data into numpy array
  test_pre = test_df[["precursor_charge"]].to_numpy()
  test_int = test_df[["target"]].to_numpy()
  test_seq = test_df[["peptide_sequence_encoded"]].to_numpy()

  test_seq = np.array(test_seq).flatten()
  test_int = np.array(test_int).flatten()
  test_pre = test_pre.flatten()

  test_seq = np.stack(test_seq, axis=0)
  test_int = np.stack(test_int, axis=0)

  np.save("test_pre.npy", test_pre)
  np.save("test_int.npy", test_int)
  np.save("test_seq.npy", test_seq)

def split_cross_val(training):
  '''
  Splits training df into 5 cross-validation splits and saves them
  '''

  splits=[]

  # shuffle the rows of the training dataframe
  training = shuffle(training)

  gkf = GroupKFold(n_splits=5)
  for train_index, valid_index in gkf.split(training, groups=training['peptide_group']):
      train_df = training.iloc[train_index]
      valid_df = training.iloc[valid_index]
      splits.append((train_df, valid_df))

  s_train_list = []
  s_valid_list = []

  for i in range(5):
      s_train = splits[i][0]
      s_valid = splits[i][1]
      s_train_list.append(s_train)
      s_valid_list.append(s_valid)


  for i in range(5):
    s_train = s_train_list[i]
    s_valid = s_valid_list[i]

    s_train_pre = s_train[["precursor_charge"]].to_numpy()
    s_train_int = s_train[["target"]].to_numpy()
    s_train_seq = s_train[["peptide_sequence_encoded"]].to_numpy()
    s_train_seq = np.array(s_train_seq).flatten()
    s_train_int = np.array(s_train_int).flatten()
    s_train_seq = np.stack(s_train_seq, axis=0)
    s_train_int = np.stack(s_train_int, axis=0)
    s_train_pre = s_train_pre.flatten()

    s_valid_pre = s_valid[["precursor_charge"]].to_numpy()
    s_valid_int = s_valid[["target"]].to_numpy()
    s_valid_seq = s_valid[["peptide_sequence_encoded"]].to_numpy()
    s_valid_seq = np.array(s_valid_seq).flatten()
    s_valid_int = np.array(s_valid_int).flatten()
    s_valid_seq = np.stack(s_valid_seq, axis=0)
    s_valid_int = np.stack(s_valid_int, axis=0)
    s_valid_pre = s_valid_pre.flatten()

    np.save(f"s{i}_train_pre.npy", s_train_pre)
    np.save(f"s{i}_train_int.npy", s_train_int)
    np.save(f"s{i}_train_seq.npy", s_train_seq)
    np.save(f"s{i}_valid_pre.npy", s_valid_pre)
    np.save(f"s{i}_valid_int.npy", s_valid_int)
    np.save(f"s{i}_valid_seq.npy", s_valid_seq)


def load_and_predict(model):
  # Load Holdout Set
  # Input
  hold_pre = np.load('/content/drive/MyDrive/splits/holdout/test_pre.npy')
  hold_seq = np.load('/content/drive/MyDrive/splits/holdout/test_seq.npy')
  hold_int = np.load('/content/drive/MyDrive/splits/holdout/test_int.npy')

  # One-Hot-Encoding
  # Sequence
  X_hold_seq = tf.one_hot(hold_seq, depth=22)
  # Precursor Charge
  X_hold_pre = tf.one_hot(hold_pre, depth=7)
  predictions = model.predict([X_hold_pre, X_hold_seq])
  return predictions

def spectral_angle(x, y):
  '''
  Calculates and returns a single spectral angle value
  '''
  x_norm = np.linalg.norm(x)
  y_norm = np.linalg.norm(y)
  prod = np.dot(x/x_norm, y/y_norm)
  if prod > 1.0:
    prod = 1
  return 1-2*(np.arccos(prod)/np.pi)

def calculate_spectral_angle(reference, holdout):
  '''
  Returns a numpy array of spectral angle values for reference and holdout
  '''
  spectral_angle_vals = []
  for i in range(holdout.shape[0]):
    holdout_value = holdout[i,:]
    reference_value = reference[i,:]
    spectral_angle_value = spectral_angle(holdout_value, reference_value)
    spectral_angle_vals.append(spectral_angle_value)
  return np.array(spectral_angle_vals)

def cosine_similarity(x, y):
  '''
  Calculates and returns a single cosine similarity value for x and y
  '''
  return 1 - spatial.distance.cosine(x, y)

def calculate_cosine_similarity(reference, holdout):
  '''
  Returns a numpy array of cosine similarity values for reference and holdout
  '''
  cosine_similarities = []
  for i in range(holdout.shape[0]):
    holdout_value = holdout[i,:]
    reference_value = reference[i,:]
    cosine_similarity_value = cosine_similarity(holdout_value, reference_value)
    cosine_similarities.append(cosine_similarity_value)
  return np.array(cosine_similarities)

def reduce_noise(df):
  '''
  Takes df with different intensity values for 'petide seq' + 'precursor charge' +
  'ion_type' + 'no' combination, calculates mean intensity value for each
  combination and returns the preprocessed df with new
  'mean_normalized_intensity' column
  '''
  # Reducing the noise => one normalized intensity value for the same 'petide seq' + 'precursor charge' + 'ion_type' + 'no' combination
  result = df.groupby(['peptide_sequence', 'precursor_charge', 'ion_type', 'no'])['normalized_intensity'].mean().reset_index()
  result.rename(columns={'normalized_intensity': 'mean_normalized_intensity'})
  return result

def equal_sample(df1, df2):
  '''
  Compares two dataframes in size, takes a sample of the same len as the smaller
  dataframe from the bigger one, returns two dataframes equal in size
  '''
  if len(df1) > len(df2):
    sample_size = len(df2)
    sampled_df = df1.sample(n=sample_size, replace=False)
  else:
    sample_size = len(df1)
    sampled_df = df2.sample(n=sample_size, replace=False)
  return df1, df2

def methionine_train_test_split(df, test_size=0.2):
  '''
  Splits df into three subsets: group1, group2 and group3. Takes test_size from
  each df, makes sure that tests made from group1 and group2 dfs are of equal size,
  concatenates three test_sets. That is the new test df, removes 'peptide_sequence'
  values from df. That is the training df. Returns test and training
  '''
  df_unmod = df.loc[(df['peptide_sequence'].str.contains('M')) &
                    ~(df['peptide_sequence_modified'].str.contains('O'))]
  df_mod = df.loc[(df['peptide_sequence'].str.contains('O')) &
                  ~(df['peptide_sequence_modified'].str.contains('M'))]
  df_both = df.loc[(df['peptide_sequence'].str.contains('O')) &
                   (df['peptide_sequence_modified'].str.contains('M'))]

  training_unmod, test_unmod = split_train_test(df_unmod, test_size)
  training_mod, test_mod = split_train_test(df_mod, test_size)
  test_mod, test_unmod = equal_sample(test_mod, test_unmod)

  training_both, test_both = split_train_test(df_both, test_size)

  test = pd.concat([test_mod, test_unmod, test_both])
  training = df[~df['peptide_sequence'].isin(test['peptide_sequence'])]
  return training, test

def create_proline_splits(df):
  '''
  Takes dataframe, sorts out the rows which contain at least one proline (df_proline)
  and rows without proline at all (df_no_proline), takes 10% as test set from
  each of new subsets, makes sure that training and test sets from each subset
  are equal in size, concatenates training sets.
  Returns test_proline, test_no_proline and training dataframes
  '''
  df_proline = df.loc[df['peptide_sequence'].str.contains("P")]
  df_no_proline = df.loc[~df['peptide_sequence'].str.contains("P")]

  training_proline, test_proline = split_train_test(df_proline, 0.1)
  training_no_proline, test_no_proline = split_train_test(df_no_proline, 0.1)

  test_proline, test_no_proline = equal_sample(test_proline, test_no_proline)

  training_proline, training_no_proline = equal_sample(training_proline, training_no_proline)
  training = pd.concat([training_proline, training_no_proline])
  return test_proline, test_no_proline, training

def two_sample_t_test(predictions1, predictions2):
  '''
  Takes numpy arrays predictions1 and predictions2, runs two-sample t-test and
  prints whether the results are significantly different based on 0.05 threshold
  '''
  # Conduct the two-sample t-test to compare the results from the two predictive analyses
  t_statistic, p_value = stats.ttest_ind(predictions1, predictions2)

  # Determine the significance of the difference between the results obtained from the two predictive analyses
  if np.all(p_value < 0.05):
      print("The results obtained are significantly different (p-value = {})".format(p_value))
  else:
      print("The results obtained are not significantly different (p-value = {})".format(p_value))
