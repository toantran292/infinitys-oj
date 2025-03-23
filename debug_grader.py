from grader.tasks import run_cpp_in_docker

if __name__ == "__main__":
    code = "#include<iostream>\nusing namespace std;\nint main(){int a,b;cin>>a>>b;cout<<a+b;}"
    input_data = "3 4"
    status, output = run_cpp_in_docker(code, input_data, 2, 128)
    print("Status:", status)
    print("Output:", output)