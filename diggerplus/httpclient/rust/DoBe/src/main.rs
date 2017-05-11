extern crate hyper;

use std::io::Read;
use hyper::Client;

fn main() {
    println!("Welcome to rust http!");
    let client = Client::new();
    let mut res = client.get("http://localhost:8000/api/v1/ping").
        send().unwrap();
    assert_eq!(res.status, hyper::Ok);
    println!("** Headers:\n {}", res.headers);
    let mut body = String::new();
    res.read_to_string(&mut body).unwrap();
    println!("** Body:\n {}", body);
}
