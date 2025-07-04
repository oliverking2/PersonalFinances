locals {
  dagster_webserver_lb_dns_name = aws_lb.dagster_webserver[0].dns_name
  lb_target_group_arn = aws_lb_target_group.dagster_webserver[0].arn
}

resource "aws_lb" "dagster_webserver" {
  count = 1
  # no longer than 6 characters
  name_prefix        = "dgweb-"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.dagster.id]
  subnets            = [aws_subnet.public.id]
}

resource "aws_lb_target_group" "dagster_webserver" {
  count       = 1
  # no longer than 6 characters
  name_prefix = "dgweb-"
  port        = 80
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.dagster.id
  health_check {
    path                = "/"
    interval            = 30
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
    matcher             = "200-399"
  }
}

resource "aws_lb_listener" "dagster_webserver" {
  count             = 1
  load_balancer_arn = aws_lb.dagster_webserver[0].arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = local.lb_target_group_arn
  }
}
