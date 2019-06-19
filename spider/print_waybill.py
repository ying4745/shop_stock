#!/usr/bin/python3
# DateTime: 2019/4/28 10:31
import os
import re
import win32api

from PyPDF2 import PdfFileReader, PdfFileWriter


class CropPDF():

    def __init__(self, file_dir, re_str='[0-9]{10}[A-Z0-9]{5}.pdf'):
        self.file_dir = file_dir
        self.re_str = re_str

        # 裁剪尺寸，gl gr gt gb 左 右 上 下
        self.gl = 26
        self.gr = 256
        self.gt = 164
        self.gb = 394

        self.new_file = self.file_dir + '/WorkPDF.pdf'
        self.pdfFileWriter = PdfFileWriter()

    def cut_size_pdf(self, file_name):
        # 读取PDF文件，裁剪尺寸，添加到新pdf中
        file_path = os.path.join(self.file_dir, file_name)

        pdfFileReader = PdfFileReader(file_path)
        numPages = pdfFileReader.getNumPages()

        for index in range(0, numPages):
            pageObj = pdfFileReader.getPage(index)

            pageObj.cropBox.lowerLeft = (self.gl, self.gt)
            pageObj.cropBox.upperRight = (self.gr, self.gb)

            self.pdfFileWriter.addPage(pageObj)

        # 删除原文件
        os.remove(file_path)

    def run(self):
        for file_name in os.listdir(self.file_dir):
            if re.match(self.re_str, file_name):
                self.cut_size_pdf(file_name)

        if self.pdfFileWriter.getNumPages() > 0:
            self.pdfFileWriter.write(open(self.new_file, 'wb'))

            # 调用打印机，打印合并在一起的pdf
            GHOSTSCRIPT_PATH = "C:\\Program Files\\gs\\gs9.27\\bin\\gswin64.exe"
            GSPRINT_PATH = "C:\\Program Files\\Ghostgum\\gsview\\gsprint.exe"

            # 打印设置，默认使用默认打印机
            # currentprinter = win32print.GetDefaultPrinter() -printer“打印机”

            win32api.ShellExecute(0, 'open', GSPRINT_PATH,
                                  '-ghostscript "' + GHOSTSCRIPT_PATH +
                                  '" -dPSFitPage -dFIXEDMEDIA -dPrinted -dUseCropBox ' +
                                  self.new_file,
                                  '.', 0)
            # 打印完删除
            #os.remove(self.new_file)


if __name__ == '__main__':
    crop_pdf = CropPDF(file_dir='D:/Download')
    crop_pdf.run()
