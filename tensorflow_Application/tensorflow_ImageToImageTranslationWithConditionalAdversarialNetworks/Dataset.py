import glob
import os
import tarfile
import urllib.request

import tensorflow as tf

'''
데이터셋은 아래에서 받았다.
https://people.eecs.berkeley.edu/~tinghuiz/projects/pix2pix/datasets/{}.tar.gz
이미지(원본 이미지를)를 분할(Segmentation) 해보자

나만의 이미지 데이터셋 만들기 - 텐서플로우의 API 만을 이용하여 만들자.
많은 것을 지원해주는 텐서플로우 API 만을 이용해서 만들 경우 코드가 굉장히 짧아지면서 빠르다.
하지만, 공부해야할 것이 꽤 많다. TFRecord, tf.data.Dataset API, tf.image API 등등 여러가지를 알아야 한다.

##################데이터 전처리기를 만드는 2가지 방법################# 
<첫번째 방법>은 원래의 데이터파일을 사용한다
<두번째 방법>은 TFRecord(텐서플로우의 표준 파일 형식)으로 원래의 데이터를 저장한뒤 불러오는 방식이다.

<두번째 방법>이 빠르다. 입출력(I/O 면에서 빠르다. 단일스레드를 사용하는 것은 동일하다.)

구체적으로, 
<첫번째 방법>
1. 데이터를 다운로드한다. 데이터셋이 들어있는 파일명을 들고와 tf.data.Dataset.from_tensor_slices 로 읽어들인다.
2. tf.data.Dataset API 및 여러가지 유용한 텐서플로우 API 를 사용하여 학습이 가능한 데이터 형태로 만든다. 
    -> tf.read_file, tf.random_crop, tf.image.~ API를 사용하여 논문에서 설명한대로 이미지를 전처리하고 학습가능한 형태로 만든다.
 
<두번째 방법> - 메모리에서 데이터를 읽는 데 필요한 시간이 단축된다.
1. 데이터를 다운로드한다. 데이터가 대용량이므로 텐서플로의 기본 데이터 형식인 TFRecord(프로토콜버퍼, 직렬화) 형태로 바꾼다.
    -> 텐서플로로 바로 읽어 들일 수 있는 형식, 입력 파일들을 하나의 통합된 형식으로 변환하는 것(하나의 덩어리)
    -> 정리하자면 Tensor 인데, 하나의 덩어리 형태
2. tf.data.Dataset API 및 여러가지 유용한 텐서플로우 API 를 사용하여 학습이 가능한 데이터 형태로 만든다. 
    -> tf.read_file, tf.random_crop, tf.image.~ API를 사용하여 논문에서 설명한대로 이미지를 전처리하고 학습가능한 형태로 만든다.
'''


class Dataset(object):

    def __init__(self, DB_name="maps",
                 batch_size=1, use_TFRecord=False, use_TrainDataset=False):

        self.Dataset_Path = "Dataset"
        self.DB_name = DB_name

        if use_TFRecord:
            self.Dataset_Path = "TFRecord"+self.Dataset_Path

        if not os.path.exists(self.Dataset_Path):
            os.makedirs(self.Dataset_Path)

        self.url = "https://people.eecs.berkeley.edu/~tinghuiz/projects/pix2pix/datasets/{}.tar.gz".format(self.DB_name)
        self.dataset_folder = os.path.join(self.Dataset_Path, self.DB_name)
        self.dataset_targz = self.dataset_folder + ".tar.gz"
        self.use_TFRecord = use_TFRecord

        # 학습용 데이터인지 테스트용 데이터인지 알려주는 변수
        self.use_TrainDataset = use_TrainDataset
        # Test Dataset은 무조건 하나씩 처리하자.
        if self.use_TrainDataset == False:
            self.batch_size = 1
        else:
            self.batch_size = batch_size

        # 데이터셋 다운로드 하고, use_TFRecord 가 True 이면 TFRecord 파일로 쓴다.E
        if DB_name == "cityscapes":
            self.file_size = 103441232
        elif DB_name ==  "facades":
            self.file_size = 30168306
        elif DB_name =="maps":
            self.file_size = 250242400

        self.Preparing_Learning_Dataset()
        if self.use_TrainDataset:
            if use_TFRecord:
                self.file_path_list = glob.glob(os.path.join(self.dataset_folder, "train/*"))
            else:
                self.file_path_list = glob.glob(os.path.join(self.dataset_folder, "train/*"))
        else:
            if use_TFRecord:
                self.file_path_list = glob.glob(os.path.join(self.dataset_folder, "val/*"))
            else:
                self.file_path_list = glob.glob(os.path.join(self.dataset_folder, "val/*"))

    def __repr__(self):
        return "Dataset Loader"

    def iterator(self):

        if self.use_TFRecord:
            self.TFRecord_Path = "TFRecord_Dataset"
            if not os.path.exists(self.TFRecord_Path):
                os.makedirs(self.TFRecord_Path)
            iterator, next_batch, db_length = self.Using_TFRecordDataset()
        else:
            iterator, next_batch, db_length = self.Using_TFBasicDataset()

        return iterator, next_batch, db_length

    def Preparing_Learning_Dataset(self):

        # 1. 데이터셋 폴더가 존재하지 않으면 다운로드(다운로드 시간이 굉장히 오래걸립니다.)
        if not os.path.exists(self.dataset_folder):  # 데이터셋 폴더가 존재하지 않는 다면?
            if not os.path.exists(self.dataset_targz):  # 데이터셋 압축 파일이 존재하지 않는 다면, 다운로드
                print("{} Dataset Download required.".format(self.DB_name))
                urllib.request.urlretrieve(self.url, self.dataset_targz)
                print("{} Dataset Download Completed".format(self.DB_name))

            # "{self.DB_name}.tar.gz"의 파일의 크기는 미리 구해놓음. (미리 확인이 필요함.)
            elif os.path.exists(self.dataset_targz) and os.path.getsize(
                    self.dataset_targz) == self.file_size:  # 완전한 데이터셋 압축 파일이 존재한다면, 존재한다고 print를 띄워주자.
                print("ALL {} Dataset Exists".format(self.DB_name))

            else:  # 데이터셋 압축파일이 존재하긴 하는데, 제대로 다운로드 되지 않은 상태라면, 삭제하고 다시 다운로드
                print(
                    "{} Dataset size must be : {}, but now size is {}".format(self.DB_name, self.file_size, os.path.getsize(self.dataset_targz)))
                os.remove(self.dataset_targz)  # 완전하게 다운로드 되지 않은 기존의 데이터셋 압축 파일을 삭제
                print("Deleting incomplete {} Dataset Completed".format(self.DB_name))
                print("we need to download {} Dataset again".format(self.DB_name))
                urllib.request.urlretrieve(self.url, self.dataset_targz)
                print("{} Dataset Download Completed".format(self.DB_name))

            # 2. 완전한 압축파일이 다운로드 된 상태이므로 압축을 푼다
            with tarfile.open(self.dataset_targz) as tar:
                tar.extractall(path=self.Dataset_Path)
            print("{} Unzip Completed".format(self.DB_name))
            # 3. 용량차지 하므로, tar.gz 파일을 지워주자. -> 데이터셋 폴더가 존재하므로
            # os.remove(self.file_name) # 하드디스크에 용량이 충분하다면, 굳이 필요 없는 코드다.

        else:  # 데이터셋 폴더가 존재하면 print를 띄워주자
            print("{} Dataset Folder Exists".format(self.DB_name))

        if self.use_TFRecord:
            pass
        '''3. 데이터형식을 텐서플로의 기본 데이터 형식인 TFRecord 로 바꾼다.(대용량의 데이터를 처리하므로 TFRecord를 사용하는게 좋다.)
        # 바꾸기전에 데이터를 입력, 출력으로 나눈 다음 덩어리로 저장한다. -> Generate_Batch의 map함수에서 입력, 출력 값으로 분리해도 되지만
        이런 전처리는 미리 되있어야 한다.
        '''

    def _image_preprocessing(self, image):
        '''
        Random jitter was applied by resizing the 256 x 256 input images to 286 x 286
        and then randomly cropping back to size 256 x 256
        '''
        # 1. 이미지를 읽고 나눈다.
        img = tf.read_file(image)
        img_decoded = tf.image.decode_image(img, channels=3)

        # 2. 256x512 이미지를 256x256, 256x256 2개로 나눈다.
        '''
        This op cuts a rectangular part out of image. The top-left corner of the returned image is at offset_height, 
        offset_width in image, and its lower-right corner is at offset_height + target_height, offset_width + target_width.
        
        offset_height: Vertical coordinate of the top-left corner of the result in the input.
        offset_width: Horizontal coordinate of the top-left corner of the result in the input.
        target_height: Height of the result.
        target_width: Width of the result.
        '''
        Ip = tf.image.crop_to_bounding_box(img_decoded, offset_height=0, offset_width=0, target_height=256,
                                           target_width=256)
        lb = tf.image.crop_to_bounding_box(img_decoded, offset_height=0, offset_width=256, target_height=256,
                                           target_width=256)

        # 3. gerator의 활성화 함수가 tanh이므로, 스케일을 맞춰준다.
        Ip_scaled = tf.subtract(tf.divide(tf.cast(Ip, tf.float32), 127.5), 1)  # gerator의 활성화 함수가 tanh이므로, 스케일을 맞춰준다.
        lb_scaled = tf.subtract(tf.divide(tf.cast(lb, tf.float32), 127.5), 1)  # gerator의 활성화 함수가 tanh이므로, 스케일을 맞춰준다.

        input = Ip_scaled
        label = lb_scaled

        # Train Dataset 에서만 동작하게 하기 위함
        if self.use_TrainDataset:
            # 4. 286x286으로 키운다.
            Ip_resized = tf.image.resize_images(images=Ip_scaled, size=(286, 286))
            lb_resized = tf.image.resize_images(images=lb_scaled, size=(286, 286))

            # 5. 이미지를 256x256으로 랜덤으로 자른다.
            Ip_random_crop = tf.random_crop(Ip_resized, size=(256, 256, 3))
            lb_random_crop = tf.random_crop(lb_resized, size=(256, 256, 3))

            input = Ip_random_crop
            label = lb_random_crop

        return input, label

    # 1. 메모리에 다 올려버리는 방법
    def Using_TFBasicDataset(self):

        random_file_path_list_Tensor = tf.random_shuffle(tf.constant(self.file_path_list))  # tensor에 데이터셋 리스트를 담기
        # random_file_path_list_Tensor = tf.constant(self.file_path_list) # tensor에 데이터셋 리스트를 담기
        dataset = tf.data.Dataset.from_tensor_slices(random_file_path_list_Tensor)
        dataset = dataset.map(self._image_preprocessing)
        '''
        buffer_size: A `tf.int64` scalar `tf.Tensor`, representing the
        number of elements from this dataset from which the new
        dataset will sample.

        dataset.buffer_size란 정확히 무엇인가? shuffling 할 때 몇개를 미리 뽑아서 랜덤하게 바꾸는건데 이상적으로 봤을 때 buffer_size가
        파일 개수 만큼이면 좋겠지만, 이미지 자체의 순서를 바꾸는 것이기 때문에 메모리를 상당히 많이 먹는다. (메모리가 16기가인 컴퓨터에서
        buffer_size = 5000 만되도 컴퓨터가 강제 종료 된다.)
        따라서 dataset.shuffle 의 매개 변수인 buffer_size를  1000정도로 로 설정(buffer_size가 1이라는 의미는 사용 안한다는 의미)
        
        더 좋은 방법? -> 파일명이 들어있는 리스트가  tf.data.Dataset.from_tensor_slices의 인자로 들어가기 전에 미리 섞는다.(tf.random_shuffle 을 사용)
        문제점1 -> tf.random_shuffle을 사용하려면 dataset.make_one_shot_iterator()을 사용하면 안된다. tf.random_shuffle을 사용하지 않고
        파일리스트를 램던함게 섞으려면 random 모듈의 shuffle을 사용해서 미리 self.file_path_list을 섞는다.
        문제점2 -> 한번 섞고 말아버린다. -> buffer_size를 자기 컴퓨터의 메모리에 맞게 최대한으로 써보자.
        '''
        # dataset = dataset.shuffle(buffer_size=1).repeat().batch(self.batch_size)
        dataset = dataset.shuffle(buffer_size=1000).repeat().batch(self.batch_size)

        '''
        위에서 tf.random_shuffle을 쓰고 아래의 make_one_shot_iterator()을 쓰면 오류가 발생한다. - stateful 관련 오류가 뜨는데, 추 후 해결될 듯?
        이유가 궁금하다면 아래의 웹사이트를 참고하자.
        https://stackoverflow.com/questions/44374083/tensorflow-cannot-capture-a-stateful-node-by-value-in-tf-contrib-data-api
        '''
        # iterator = dataset.make_one_shot_iterator()

        # tf.random_shuffle을 쓰려면 아래와 같이 make_initializable_iterator을 써야한다. - stack overflow 에서 찾음
        iterator = dataset.make_initializable_iterator()

        return iterator, iterator.get_next(), len(self.file_path_list)

    # 2. 텐서플로로 바로 읽어 들일 수 있는 방법
    def Using_TFRecordDataset(self):
        pass
        # 4. TFRecordDataset()사용해서 읽어오기 -> 저장하기 전에 셔플해서 저장하자
        # file_name = tf.placeholder(tf.string, shape=[None])
        # dataset = tf.data.TFRecordDataset(file_name)
        # dataset = dataset.map()  #
        # dataset = dataset.repeat()
        # dataset = dataset.batch(batch_size=self.batch_size)
        # iterator = dataset.make_initializable_iterator()
        # training_file_name = ["", ""]
        # return iterator


if __name__ == "__main__":
    '''
    Dataset 은 아래에서 하나 고르자
    "cityscapes"
    "facades"
    "maps"
    '''
    dataset = Dataset(DB_name="cityscapes", batch_size=4, use_TFRecord=False, use_TrainDataset=True)
    iterator, next_batch, data_length = dataset.iterator()

else:
    print("Dataset imported")
