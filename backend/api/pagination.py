# api/pagination.py  (create this if you don’t have it)
from rest_framework.pagination import PageNumberPagination

class LimitPageNumberPagination(PageNumberPagination):
    page_size = 6                 # default page size
    page_size_query_param = "limit"
    max_page_size = 100