from django.shortcuts import render


from django.shortcuts import render,get_object_or_404
def custom_404(request, exception):
    return render(request, '404_page/404.html', status=404)

