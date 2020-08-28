from functions import *

parse_input()
conversion_table = get_conversion_table()
bmp_data = read_bmp()
converted_data = convert(conversion_table, bmp_data)
write(converted_data)
