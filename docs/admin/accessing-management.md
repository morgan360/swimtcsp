# Accessing Management

@login\_required() @user\_in\_group('Manager') def management(request): return render(request, 'management.html')

This code is used to restrict access to management page. The code is located in Home App
